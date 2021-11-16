import argparse
import re

from flask import jsonify, request
from flask_classful import FlaskView
from flask_cors import cross_origin

from wisdomify import flows
from wisdomify.connectors import connect_to_wandb, connect_to_es

from wisdomify.docs import Story
from wisdomify.flows import SearchFlow, Wisdom2DefFlow
from wisdomify.loaders import load_config, load_device
from wisdomify.wisdomifier import Wisdomifier


class WisdomifyView(FlaskView):
    """
    sents -> wisdoms
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("--ver", type=str,
                        default='a',
                        required=True,
                        help="This parameter is used for wisdomifyAPI deployment."
                             "The parameter should be the model version described on WandB.")
    parser.add_argument("--model", type=str,
                        default='rd_beta',
                        required=True,
                        help="This parameter is used for wisdomifyAPI deployment."
                             "The parameter should be the model name described on WandB.")

    args = parser.parse_args()
    ver = args.ver
    model = args.model

    config = load_config()[model][ver]
    device = load_device(False)
    with connect_to_wandb(job_type="infer", config=config) as run:
        # --- init a wisdomifier --- #
        flow = flows.ExperimentFlow(run, model, ver, device)("d", config)
    # --- wisdomifier is independent of wandb run  --- #
    wisdomifier = Wisdomifier(flow.rd_flow.rd, flow.datamodule)

    @cross_origin(origin='*')
    def index(self):
        form = request.args
        sent = form['sent']
        size = int(form['size']) if 'size' in form.keys() else 10

        results = self.wisdomifier(sents=[sent])[0][:size]
        response = jsonify(
            list(zip(*sorted(results, key=lambda k: k[1], reverse=True)))
        )

        return response


class StorytellView(FlaskView):
    """
    wisdoms -> examples & definitions
    """
    es = connect_to_es()
    index_name = ",".join(name for name in Story.all_names())
    size = 5

    config = {'data': 'wisdoms', 'ver': 'a', 'val_ratio': None, 'seed': 410, 'upload': False}
    run = connect_to_wandb(job_type="download", config=config)
    wisdom2DefFlow = Wisdom2DefFlow(run, config['ver'])
    wisdom2DefFlow.download_raw_df()

    def egs(self):
        form = request.args
        wisdom = form['wisdom']

        flow = SearchFlow(self.es, self.index_name, self.size)(wisdom)
        res = flow.res

        if res:
            return jsonify([
                {
                    "index": hit['_index'],
                    "highlight": re.sub('[<em></em>]', '', hit['highlight']['sents'][0])
                }
                for hit in res['hits']['hits']
            ])

        else:
            return jsonify(f"No data for '{wisdom}'"), 404

    def defs(self):
        form = request.args
        wisdom = form['wisdom']

        defs = self.wisdom2DefFlow.raw_df\
            .loc[self.wisdom2DefFlow.raw_df['wisdom'] == wisdom]['def']\
            .to_list()

        if defs:
            return jsonify(defs)

        else:
            return jsonify(f"No data for '{wisdom}'"), 404

