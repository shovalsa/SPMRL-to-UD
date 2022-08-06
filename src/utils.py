import re
from io import StringIO
import pandas as pd
import requests
import logging

logger = logging.getLogger()


def parse_yap_output(output, ents):
    tsv = StringIO(output)
    columns = ["ID", "FORM", "LEMMA", "XPOS", "UPOS", "FEATS", "HEAD", "DEPREL", "MISC1", "ENTS"]
    df = pd.read_csv(tsv, sep="\t", names=columns, keep_default_na=False, quotechar="\'")
    df["ENTS"] = ""
    for ent in ents:
        start = int(ent["start"])
        end = int(ent["end"])
        if end > start:
            df.loc[start:end-1, "ENTS"] = ent["label"]
        else:
            df.loc[start, "ENTS"] = ent["label"]
    return df


def handle_punct(text):
    text = re.sub('([!#$%&\()*+,-./:;<=>?@\^_|~])', r' \1 ', text)
    text = re.sub(r' +', ' ', text)
    text = text.replace('. ', '.  ')
    return text


def handle_quotes(text):
    text = re.sub('(\s[\'\"`])', r' \1 ', text)  # beginning of quote
    text = re.sub('([\'\"`]\s)', r' \1 ', text)  # end of quote
    text = re.sub('(^[\'\"`])', r' \1 ', text)  # sentence starts with quote
    text = re.sub('([\'\"`]$)', r' \1 ', text)  # sentence ends with quote
    text = re.sub('(\w{1,3})([\'\"`])(\w{2,})', r' \2 \1\3', text)
    return text


def call_api(text, url, method="yap/heb/joint", use_nemo=False):
    port = "8090" if use_nemo else "8000"
    url = f'{url}:{port}/{method}'  # change this if you refer to a remote YAP server
    nemo_key = "nemo_multi_align_morph" if method in ["multi_align_hybrid", "morph_hybrid"] else "nemo_morph"
    text_to_sentences = re.split(r"(?<=\S[\.\?\!]\s)", text)
    for txt in text_to_sentences:
        sentence = handle_punct(txt)
        sentence = handle_quotes(sentence)
        param = "sentences" if use_nemo else "text"
        ents = []
        response = requests.post(url,
                                 headers={'accept': 'application/json', 'Content-Type': 'application/json'},
                                 json={param: sentence},
                                 params={'verbose': 2, 'include_yap_outputs': True})
        content = response.json()
        if content:
            if use_nemo:
                ents = content[0]["ents"]["morph"] if use_nemo else []
                ents = ents[nemo_key] if ents else []
                content = content[0]["dep_tree"] if use_nemo else content["dep_tree"]
            else:
                content = content["dep_tree"]
        else:
            sentence = '{"text":"  %s  "}' % sentence
            sentence = sentence.encode('utf-8')
            response = requests.post(url,
                                     headers={'accept': 'application/json', 'Content-Type': 'application/json'},
                                     data=sentence,
                                     params={'verbose': 2, 'include_yap_outputs': True})
            content = response.json()
            try:
                content = content["dep_tree"]
            except Exception as e:
                logger.error(f"Parsing failed. Try another method (e.g. morph_hybrid): {e}")
        yield txt, content, ents

