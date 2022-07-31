import re
from io import StringIO
import pandas as pd
import requests


def parse_yap_output(output):
    print(output)
    print([l.split("\t") for l in output.split("\n") if l])
    tsv = StringIO(output)
    columns = ["ID", "FORM", "LEMMA", "XPOS", "UPOS", "FEATS", "HEAD", "DEPREL", "MISC1", "MISC2"]

    return pd.read_csv(tsv, sep="\t", names=columns, keep_default_na=False)


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


def call_api(text):
    text = handle_punct(text)
    text = handle_quotes(text)
    url = 'http://127.0.0.1:8000/yap/heb/joint'  # change this if you refer to a remote YAP server
    text = '{"text":"  %s  "}' % text
    text = text.encode('utf-8')
    response = requests.post(url,
                             headers={'accept': 'application/json', 'Content-Type': 'application/json'},
                             data=text,
                             params={'verbose': 2, 'include_yap_outputs': True})
    content = response.json()
    return content["dep_tree"]
