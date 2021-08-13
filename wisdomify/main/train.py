import pytorch_lightning as pl
import torch
import argparse
from pytorch_lightning.callbacks import ModelCheckpoint
from transformers import AutoModelForMaskedLM, AutoTokenizer
from wisdomify.loaders import load_conf
from wisdomify.models import RD
from wisdomify.builders import build_vocab2subwords
from wisdomify.paths import DATA_DIR
from wisdomify.vocab import VOCAB
from wisdomify.datasets import WisdomDataModule
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
    # parameters from conf
    conf = load_conf()
    bert_model: str = conf['versions'][ver]['bert_model']
    k: int = conf['versions'][ver]['k']
    lr: float = conf['versions'][ver]['lr']
    max_epochs: int = conf['versions'][ver]['max_epochs']
    batch_size: int = conf['versions'][ver]['batch_size']
    repeat: bool = conf['versions'][ver]['repeat']
    shuffle: bool = conf['versions'][ver]['shuffle']
    num_workers: int = conf['versions'][ver]['num_workers']
    data_version: str = conf['versions'][ver]['data_version']
    # TODO: should enable to load both example and definition on one dataset
    data_name: str = conf['versions'][ver]['data_name'][0]
    train_ratio: float = conf['versions'][ver]['train_ratio']
    test_ratio: float = conf['versions'][ver]['test_ratio']

    if ver == "0":
        model_name = "wisdomify_def_{epoch:02d}_{train_loss:.2f}"
    else:
        raise NotImplementedError

    # --- instantiate the model --- #
    kcbert_mlm = AutoModelForMaskedLM.from_pretrained(bert_model)
    tokenizer = AutoTokenizer.from_pretrained(bert_model)

    vocab2subwords = build_vocab2subwords(tokenizer, k, VOCAB).to(device)
    rd = RD(kcbert_mlm, vocab2subwords, k, lr)  # mono rd
    rd.to(device)
    # --- setup a dataloader --- #
    data_module = WisdomDataModule(data_version=data_version,
                                   data_name=data_name,
                                   k=k,
                                   device=device,
                                   vocab=VOCAB,
                                   tokenizer=tokenizer,
                                   batch_size=batch_size,
                                   num_workers=num_workers,
                                   train_ratio=train_ratio,
                                   test_ratio=test_ratio,
                                   shuffle=shuffle,
                                   repeat=repeat)

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

    # data_module.prepare_data()
    # data_module.setup(stage='fit')

    trainer.fit(model=rd, datamodule=data_module)

    # TODO: validate every epoch and test model after training
    '''
    trainer.validate(model=rd,
                     valid_loader=valid_loader)

    trainer.test(model=rd,
                 test_loader=test_loader)
    '''


if __name__ == '__main__':
    main()
