import re
from io import StringIO
import pandas as pd
import requests


def parse_yap_output(output):
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


def call_api(text, url, port):
    url = f'{url}:{port}/yap/heb/joint'  # change this if you refer to a remote YAP server
    text_to_sentences = re.split(r"(?<=\S[\.\?\!]\s)", text)
    for txt in text_to_sentences:
        sentence = handle_punct(txt)
        sentence = handle_quotes(sentence)
        try:
            response = requests.post(url,
                                     headers={'accept': 'application/json', 'Content-Type': 'application/json'},
                                     json={'text': sentence},
                                     params={'verbose': 2, 'include_yap_outputs': True})
            content = response.json()
            content = content["dep_tree"]
        except KeyError:
            sentence = '{"text":"  %s  "}' % sentence
            sentence = sentence.encode('utf-8')
            response = requests.post(url,
                                     headers={'accept': 'application/json', 'Content-Type': 'application/json'},
                                     data=sentence,
                                     params={'verbose': 2, 'include_yap_outputs': True})
            content = response.json()
            content = content["dep_tree"]
        yield txt, content


def call_nemo_api(text, method, url, port):
    url = f'{url}:{port}/{method}'  # change this if you refer to a remote YAP server
    response = requests.post(url,
                             headers={'accept': 'application/json', 'Content-Type': 'application/json'},
                             json={'sentences': text, 'tokenized': False},
                             params={"verbose": 2, "include_yap_outputs": True})
    content = response.json()
    print(content)