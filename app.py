from flask import Flask, request
from flask_cors import CORS
from waitress import serve
from routes.dim_cis import Beam
from routes.propriedades_materiais import Concreto

app = Flask(__name__)
CORS(app)

@app.route('/', methods=['GET', 'POST'])
def index():
    return "Hello, World! Sou o backend do treinamento de Python para Engenharia Estrutural!"

@app.route('/dim-cis', methods=['POST', 'GET'])
def dim_cis():
    data = request.get_json()
    name = data['name']
    bw = float(data['bw'])
    h = float(data['h'])
    Vk = float(data['Vk'])
    gama_c = float(data['gama_c'])
    gama_c2 = float(data['gama_c2'])
    fywk = float(data['fywk'])
    gama_s = float(data['gama_s'])
    fck = float(data['fck'])
    stirrupLeg = float(data['stirrupLeg'])

    beam = Beam(name, bw, h, Vk, gama_c, gama_c2, fywk, gama_s, fck, stirrupLeg)
    results = beam.results_dim_cis()

    return results

@app.route('/concreto-prop', methods=['POST', 'GET'])
def concreto_prop():
    data = request.get_json()
    fck = float(data['fck'])  # Parâmetro obrigatório
    
    # Parâmetros opcionais
    dias = float(data.get('dias', 28))
    gama_c = float(data.get('gama_c', 1.4))
    alfa_e = float(data.get('alfa_e', 0.8))
    alfa_fator = float(data.get('alfa_fator', 1.5))
    epsilon_c = float(data.get('epsilon_c', 0.002))
    epsilon_t = float(data.get('epsilon_t', 0.00015))

    conc = Concreto(fck, dias, gama_c, alfa_e, alfa_fator, epsilon_c, epsilon_t)
    results = conc.all_methods()

    return results

if __name__ == '__main__':
    print("Servidor rodando na porta 8080...")
    serve(app, host='0.0.0.0', port=8080)
