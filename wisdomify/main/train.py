import sys
sys.path.append('../..')
import pytorch_lightning as pl
import torch
import argparse
from pytorch_lightning.callbacks import ModelCheckpoint
from torch.utils.data import DataLoader
from transformers import AutoModelForMaskedLM, AutoTokenizer
from wisdomify.loaders import load_wisdom2def, load_conf, load_wisdom2eg
from wisdomify.models import RD
from wisdomify.builders import build_vocab2subwords, build_X, build_y
from wisdomify.paths import DATA_DIR
from wisdomify.vocab import VOCAB
from wisdomify.datasets import Wisdom2EgDataModule
from pytorch_lightning.loggers import TensorBoardLogger


def main():
    # --- setup the device --- #
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    # --- prep the arguments --- #
    parser = argparse.ArgumentParser()
    parser.add_argument("--ver", type=str,
                        default="0")
    args = parser.parse_args()
    ver: str = args.ver
    conf = load_conf()
    bert_model: str = conf['bert_model']
    data: str = conf['versions'][ver]['data']
    k: int = conf['versions'][ver]['k']
    lr: float = conf['versions'][ver]['lr']
    max_epochs: int = conf['versions'][ver]['max_epochs']
    batch_size: int = conf['versions'][ver]['batch_size']
    repeat: int = conf['versions'][ver]['repeat']
    num_workers: int = conf['versions'][ver]['num_workers']
    shuffle: bool = conf['versions'][ver]['shuffle']

    # --- the type of wisdomifier --- #
    if data == "wisdom2def":
        # wisdom2sent = load_wisdom2def()
        model_name = "wisdomify_def_{epoch:02d}_{train_loss:.2f}"
    elif data == "wisdom2eg":
        # wisdom2sent = load_wisdom2eg()
        model_name = "wisdomify_eg_{epoch:02d}_{train_loss:.2f}"
    else:
        raise NotImplementedError("Invalid data provided")
    # --- instantiate the model --- #
    kcbert_mlm = AutoModelForMaskedLM.from_pretrained(bert_model)
    tokenizer = AutoTokenizer.from_pretrained(bert_model)

    vocab2subwords = build_vocab2subwords(tokenizer, k, VOCAB).to(device)
    rd = RD(kcbert_mlm, vocab2subwords, k, lr)  # mono rd
    rd.to(device)
    # --- setup a dataloader --- #
    wisdom2eg_data_module = Wisdom2EgDataModule(k = k,
                                                device=device,
                                                VOCAB=VOCAB,
                                                tokenizer=tokenizer,
                                                batch_size=batch_size,
                                                num_workers=num_workers)

    wisdom2eg_data_module.prepare_data()
    wisdom2eg_data_module.setup()

    train_loader = wisdom2eg_data_module.train_dataloader()
    valid_loader = wisdom2eg_data_module.valid_dataloader()
    test_loader = wisdom2eg_data_module.test_dataloader()

    # --- init callbacks --- #
    checkpoint_callback = ModelCheckpoint(
        monitor='train_loss',
        filename=model_name
    )
    # --- instantiate the logger --- #
    logger = TensorBoardLogger(save_dir=DATA_DIR,
                               name="lightning_logs")

    # --- instantiate the trainer --- #
    trainer = pl.Trainer(gpus=torch.cuda.device_count(),
                         max_epochs=max_epochs,
                         callbacks=[checkpoint_callback],
                         default_root_dir=DATA_DIR,
                         logger=logger)
    # --- start training --- #
    trainer.fit(model=rd,
                train_dataloader=train_loader)

    # TODO: validate every epoch and test model after training
    '''
    trainer.validate(model=rd,
                     valid_loader=valid_loader)

    trainer.test(model=rd,
                 test_loader=test_loader)
    '''

if __name__ == '__main__':
    main()
