# OpenStruct

descrição do projeto

## Acesso a API

Adicionar orientações para acessar a API.

## Rotas disponíveis 

### /dim-cis

[POST]: Realiza o dimensionamento de uma viga de concreto armado ao cisalhamento. 

#### REQUEST

Method: POST

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

#### RESPONSE

```JSON
{
    "results_compressed_cis": {
        "Vd (kN)": 140.0,
        "Vrd2 (kN)": 687.3428571428573,
        "alphaV2": 0.88,
        "status": "ok"
    },
    "results_concrete": {
        "fcd (MPa)": 21.42857142857143,
        "fck (MPa)": 30.0,
        "fctd (MPa)": 1.4482340769084445,
        "fctk_inf (MPa)": 2.027527707671822,
        "fctm (MPa)": 2.896468153816889,
        "fywd (MPa)": 434.7826086956522
    },
    "results_detailing": {
        "Diameter (mm)": [5.0, 6.3, 8.0, 10.0, 12.5, 16.0, 20.0, 25.0, 32.0, 40.0],
        "Spacing (cm)": [11.0, 17.0, 28.0, 45.0, 70.0, 115.0, 180.0, 282.0, 462.0, 723.0]
    },
    "results_tension": {
        "StatusTension": "aws = armadura minima",
        "Vc (kN)": 117.30696022958399,
        "Vrd3_min (kN)": 178.51059165371478,
        "Vsw_min (kN)": 61.20363142413079,
        "asw_adot (cm2/m)": 3.475761784580267,
        "asw_min (cm2/cm)": 0.03475761784580267,
        "asw_min (cm2/m)": 3.475761784580267
    }
}

```








