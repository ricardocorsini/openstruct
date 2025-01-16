# 'http://167.114.5.192:8080/concreto-prop'

import requests

json_data = {
    'fck': 30,
    'dias': 28, 
    'gama_c': 1.4, 
    'alfa_e': 0.8, 
    'alfa_fator': 1.5, 
    'epsilon_c': 0.002, 
    'epsilon_t': 0.00015
}

response = requests.post('http://localhost:8080/concreto-prop', 
                         json=json_data
                         )
print(response.text)
