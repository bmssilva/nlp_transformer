
# Código elaborado com base do tutorial disponível em 
# https://www.youtube.com/watch?v=cyCb2yZthmg&list=PLLrlHSmC0Mw73a1t73DEjgGMPyu8QssWT&index=51
# colab https://colab.research.google.com/drive/1dBIKowtIEhM8MaPgDTkBvPLhikCuxOsU?usp=sharing

# Utilizado um modelo de linguagem neural para treinar uma máquina de tradução Inglês-Português.
# Lendo o córpus e separando em conjuntos de treino e teste"""

from translate.storage.tmx import tmxfile
from random import shuffle

# ler córpus 
# utilizado um córpus de legendas de TED talks https://object.pouta.csc.fi/OPUS-TED2020/v1/tmx/en-pt_br.tmx.gz
with open("en-pt_br.tmx\\en-pt_br.tmx", 'rb') as fin:
  f = tmxfile(fin, 'en', 'pt')

prefixo = '>>pt_br<<'
# formatar as traduções corretamente
data = [{ 'src': prefixo + ' ' + w.source, 'trg': w.target } for w in f.unit_iter()]
# embaralhar os pares
shuffle(data)
# separar em conjuntos de treino e teste
size = int(len(data) * 0.2)
treino = data[size:][:10000]
teste = data[:size][:1000]

treino[10]

"""Definindo parâmetros do modelo e treinamento"""

learning_rate = 1e-5 # taxa de aprendizado
epocas = 5 # número de épocas
batch_size = 16 # tamanho do batch
batch_status = 32
early_stop = 5
write_path='model.pt' # caminho para salvar o melhor modelo

"""Separando dados em batches"""

from torch.utils.data import DataLoader

traindata = DataLoader(treino, batch_size=batch_size, shuffle=True)
devdata = DataLoader(teste, batch_size=batch_size, shuffle=True)

"""Método de Avaliação"""

from nltk.translate.bleu_score import corpus_bleu
def evaluate(tokenizer, model, devdata, batch_size, batch_status, device):
    model.eval()
    y_real = []
    y_pred = []
    for batch_idx, inp in enumerate(devdata):
        y_real.extend(inp['trg'])
        # tokenize
        model_inputs = tokenizer(inp['src'], truncation=True, padding=True, max_length=128, return_tensors="pt").to(device)
        # Translate
        generated_ids = model.generate(**model_inputs, num_beams=1)
        # Post-process translation
        output = tokenizer.batch_decode(generated_ids, skip_special_tokens=True)
        y_pred.extend(output)

        # Display
        if (batch_idx+1) % batch_status == 0:
            print('Evaluation: [{}/{} ({:.0f}%)]'.format(batch_idx+1, \
                len(devdata), 100. * batch_idx / len(devdata)))

    # evaluating based on bleu
    hyps, refs = [], []
    for i, snt_pred in enumerate(y_pred):
        hyps.append(nltk.word_tokenize(snt_pred))
        refs.append([nltk.word_tokenize(y_real[i])])
    bleu = corpus_bleu(refs, hyps)

    return bleu

"""Método de Treinamento"""

def train(tokenizer, model, traindata, devdata, optimizer, num_epochs, batch_size, batch_status, device, early_stop=5, write_path='model.pt'):
  max_bleu = evaluate(tokenizer, model, devdata, batch_size, batch_status, device)
  print('BLEU inicial:', max_bleu)
  model.train()
  repeat = 0
  for epoch in range(num_epochs):
    losses = []
    batch_src, batch_trg = [], []

    for batch_idx, inp in enumerate(traindata):
        # Init
        optimizer.zero_grad()

        # tokenize
        model_inputs = tokenizer(inp['src'], truncation=True, padding=True, max_length=128, return_tensors="pt").to(device)
        with tokenizer.as_target_tokenizer():
          labels = tokenizer(inp['trg'], truncation=True, padding=True, max_length=128, return_tensors="pt").input_ids.to(device)
        # translate
        output = model(**model_inputs, labels=labels) # forward pass

        # Calculate loss
        loss = output.loss
        losses.append(float(loss))

        # Backpropagation
        loss.backward()
        optimizer.step()

        batch_src, batch_trg = [], []

        # Display
        if (batch_idx+1) % batch_status == 0:
            print('Train Epoch: {} [{}/{} ({:.0f}%)]\tLoss: {:.6f}\tTotal Loss: {:.6f}'.format(
            epoch, batch_idx+1, len(traindata), 100. * batch_idx / len(traindata), float(loss), round(sum(losses) / len(losses), 5)))

    bleu = evaluate(tokenizer, model, devdata, batch_size, batch_status, device)
    print('BLEU:', bleu)
    if bleu > max_bleu:
        max_bleu = bleu
        repeat = 0

        print('Saving best model...')
        torch.save(model, write_path)
    else:
        repeat += 1

    if repeat == early_stop:
        break

"""Inicializando o Modelo"""

import nltk
nltk.download('punkt')
import torch
from torch import optim
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM

device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
model = AutoModelForSeq2SeqLM.from_pretrained("Helsinki-NLP/opus-mt-en-ROMANCE").to(device)
tokenizer = AutoTokenizer.from_pretrained("Helsinki-NLP/opus-mt-en-ROMANCE")

"""Treinando"""

optimizer = optim.AdamW(model.parameters(), lr=learning_rate)
train(tokenizer, model, traindata, devdata, optimizer, epocas, batch_size, batch_status, device, early_stop, write_path)

# sentenças a serem traduzidas
batch_input_str = ((">>pt_br<< We can do better, America can do better, and help is on the way."),
                   (">>pt_br<< Equal access to public education has been gained."),
                   (">>pt_br<< We thought that these elections would bring the Iraqis together, and that as we trained Iraqi security forces we could accomplish our mission with fewer American troops."))
# tokenizando as sentenças
encoded = tokenizer(batch_input_str, return_tensors='pt', padding=True).to(device)
# traduzindo
translated = model.generate(**encoded)
# preparando a saída
tokenizer.batch_decode(translated, skip_special_tokens=True)

# Salvando o modelo
model.save_pretrained('tradutor_modelo_en_pt')
tokenizer.save_pretrained('tradutor_tokenizer_en_pt')