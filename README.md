# OpenStruct

descrição do projeto

## Acesso a API

```python
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

```

## Rotas disponíveis 

### /dim-cis

[POST]: Realiza o dimensionamento de uma viga de concreto armado ao cisalhamento. 

```python
import requests

json_data = {
    'name': 'V1', # Nome da viga
    'bw': 30.0, # Largura da viga (cm)
    'h': 50.0, # Altura da viga (cm)
    'Vk': 100.0, # Força cortante característica (kN)
    'gama_c': 1.4, # Coeficiente de minoração do concreto
    'gama_c2': 1.4, # Coeficiente de majoração da força cortante
    'fywk': 500.0, # Tensão de escoamento característica do aço (MPa)
    'gama_s': 1.15, # Coeficiente de minoração do aço
    'fck': 30.0, # Resistência característica à compressão do concreto (MPa)
    'stirrupLeg': 2 # Número de ramos do estribo
}

response = requests.post('http://167.114.5.192:8080/dim-cis', 
                         json=json_data
                         )
print(response.text)

```





