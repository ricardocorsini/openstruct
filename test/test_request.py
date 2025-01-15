import requests

json_data = {
    'name': 'V1',
    'bw': 30.0,
    'h': 50.0,
    'Vk': 100.0,
    'gama_c': 1.4,
    'gama_c2': 1.4,
    'fywk': 500.0,
    'gama_s': 1.15,
    'fck': 30.0,
    'stirrupLeg': 2
}

response = requests.post('http://167.114.5.192:8080/dim-cis', 
                         json=json_data
                         )
print(response.text)
