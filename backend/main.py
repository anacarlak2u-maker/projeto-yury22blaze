from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
from threading import Thread, Lock
import requests, json, time, logging
from datetime import datetime

app = Flask(__name__)
CORS(app)
estado_lock = Lock()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

analise_sinal = False
entrada = 0
max_gale = 2
resultado = []
check_resultado = []
cor_sinal = ''
cores = []

placar = {'win_primeira': 0, 'win_gale1': 0, 'win_gale2': 0, 'win_branco': 0, 'loss': 0,
          'consecutivas': 0, 'max_consecutivas': 0, 'sinais_hoje': 0}

estado_site = {'sinal_ativo': False, 'ultimo_sinal': None, 'online': True,
               'historico_sinais': [], 'ultima_atualizacao': None, 'placar': placar.copy()}

@app.route('/')
def serve_index():
    return send_from_directory('.', 'index.html')

@app.route('/api/status')
def get_status():
    with estado_lock:
        hoje = datetime.now().strftime('%d/%m/%Y')
        sinais_hoje = len([s for s in estado_site['historico_sinais']
                           if s.get('data_completa', '').startswith(hoje.split('/')[0])])
        estado_site['placar']['sinais_hoje'] = sinais_hoje
        return jsonify({
            'online': estado_site['online'],
            'sinal_ativo': estado_site['sinal_ativo'],
            'ultimo_sinal': estado_site['ultimo_sinal'],
            'ultima_atualizacao': estado_site['ultima_atualizacao'],
            'placar': estado_site['placar'],
            'historico_sinais': estado_site['historico_sinais'],
            'timestamp': time.time()
        })

@app.route('/api/ultimos_resultados')
def ultimos_resultados():
    try:
        req = requests.get('https://blaze.bet.br/api/singleplayer-originals/originals/roulette_games/recent/1', timeout=10)
        data = json.loads(req.content)
        resultados = []
        for jogo in data:
            numero = jogo['roll']
            if 1 <= numero <= 7:
                cor, emoji = 'V', '🔴'
            elif 8 <= numero <= 14:
                cor, emoji = 'P', '⚫'
            else:
                cor, emoji = 'B', '⚪'
            resultados.append({'numero': numero, 'cor': cor, 'emoji': emoji})
        return jsonify(resultados)
    except Exception as e:
        logging.error(f"Erro: {e}")
        return jsonify([])

def reset():
    global analise_sinal, entrada
    entrada = 0
    analise_sinal = False
    with estado_lock:
        estado_site['sinal_ativo'] = False

def enviar_sinal(cor, padrao):
    global analise_sinal, cor_sinal
    sinal = {
        'id': len(estado_site['historico_sinais']) + 1,
        'padrao': padrao, 'cor': cor,
        'timestamp': datetime.now().strftime('%H:%M:%S'),
        'data_completa': datetime.now().strftime('%d/%m/%Y %H:%M:%S'),
        'resultado': None, 'status': 'ATIVO'
    }
    with estado_lock:
        estado_site['sinal_ativo'] = True
        estado_site['ultimo_sinal'] = sinal
        estado_site['historico_sinais'].append(sinal)
        estado_site['ultima_atualizacao'] = datetime.now().strftime('%H:%M:%S')
    analise_sinal = True
    cor_sinal = cor
    logging.info(f"Sinal enviado: {padrao} - {cor}")

def monitorar():
    logging.info("Monitorando Blaze...")
    while True:
        try:
            req = requests.get('https://blaze.bet.br/api/singleplayer-originals/originals/roulette_games/recent/1', timeout=10)
            data = json.loads(req.content)
            jogo = [x['roll'] for x in data]
            if jogo != check_resultado:
                check_resultado[:] = jogo
                enviar_sinal('🛑', 'Exemplo Sinal')
            time.sleep(10)
        except Exception as e:
            logging.error(e)
            time.sleep(10)

if __name__ == '__main__':
    Thread(target=monitorar, daemon=True).start()
    app.run(host='0.0.0.0', port=5000)
