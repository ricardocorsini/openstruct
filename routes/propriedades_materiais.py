"""
Script desenvolvido no treinamento de Python para Engenharia Estrutural. 
Autor: Eduardo XXXXXXXX (Aluno)
github: XXXXXXXXXX
"""

#############################################################################################################################
#############################################################################################################################
#######################################           PROPRIEDADE DOS MATERIAIS           #######################################
#############      PROGRAMA QUE REUNE AS PRINCIPAIS PROPRIEDADES DOS MATERIAIS, BASEADOS NA NBR 6118, 2023      #############
#############################################################################################################################
#############################################################################################################################

######## LER READ.ME ########
######## LER READ.ME ########
######## LER READ.ME ########

import numpy as np
import math

class Concreto:
    '''
    ## Concreto

    Tenta reunir as diversas propriedades básicas do concreto.

    - #### Obrigatórios:

      - fck= ___: Resistência característica à compressão em MPa.

    - #### Opcionais:

      - dias = 28: Data que se deseja avaliar o concreto;  

      - gama_c = 1.4: Coeficiente de ponderação de resistência do concreto;  

      - alfa_e = 0.8: Fator alfa e que varia conforme o agregado utilizado no concreto (ver NBR 6118:2023 - 8.2.8). A sugestão inicial é 0.8, valor aproximado para o Rio de Janeiro;  

      - alfa_fator = 1.5: Fator alfa, associado a forma geométrica do elemento analisado. É utilizado para determinar o momento de fissuração, entre outras aplicações. Ver NBR 6118:2023 - 17.3.1;  

      - epsilon_c = 0.002: Deformação específica que a peça está imposta, caso comprimida;  

      - epsilon_t = 0.00015: Deformação específica que a peça está imposta, caso tracionada.  
    '''

    def __init__(self, fck, dias = 28, gama_c = 1.4, alfa_e = 0.8, alfa_fator = 1.5, epsilon_c = 0.002, epsilon_t = 0.00015):
        self.fck = fck          ## HOLD: FAZER TRATAMENTO PARA NÃO ACEITAR FCK MENOR QUE 20MOA OU MAIOR QUE 90MPA
        self.dias = dias
        self.gama_c = gama_c
        self.alfa_e = alfa_e
        self.alfa_fator = alfa_fator
        self.epsilon_c = epsilon_c
        self.epsilon_t = epsilon_t

    def taxaMinima(self):
        '''Taxa mínima para armadura de flexão (ro,mín) (NBR 6118:2023 - 17.3.5.2.1 - Tabela 17.3)'''
        if self.fck <= 30:
            ro_min = 0.00150
        elif self.fck <= 35:
            ro_min = 0.00164
        elif self.fck <= 40:
            ro_min = 0.00179
        elif self.fck <= 45:
            ro_min = 0.00194
        elif self.fck <= 50:
            ro_min = 0.00208
        elif self.fck <= 55:
            ro_min = 0.00211
        elif self.fck <= 60:
            ro_min = 0.00219
        elif self.fck <= 65:
            ro_min = 0.00226
        elif self.fck <= 70:
            ro_min = 0.00233
        elif self.fck <= 75:
            ro_min = 0.00239
        elif self.fck <= 80:
            ro_min = 0.00245
        elif self.fck <= 85:
            ro_min = 0.00251
        elif self.fck <= 90:
            ro_min = 0.00256 
        return ro_min

    def fckj(self):
        '''fckj - resistência do concreto a compressão em determinada data menor que 28dias (NBR 6118:2023 - 12.3.3)'''
        beta = np.exp(0.38 * (1 - pow((28 / self.dias), 0.5)))
        fckj_dias = beta * self.fck
        return fckj_dias
    
    def fctm(self):
        '''fctm - Resistência média à tração do concreto (NBR 6118:2023 - 8.2.5)'''
        if self.fck <= 50:
            fct_m = 0.3 * pow(self.fck, (2 / 3))
        elif self.fck <= 90:
            fct_m = 2.12 * np.log(1 + 0.11 * self.fck)
        return fct_m

    def fctmj(self):
        '''fctmj - Resistência média à tração do concreto em data inferior aos 28 dias, desde que fckj >= 7MPa (NBR 6118:2023 - 8.2.5)'''
        # HOLD: Implementar aviso para fckj < 7MPa
        if self.fck <= 50:
            fct_mj = 0.3 * pow(self.fckj(), (2 / 3))
        elif self.fck <= 90:
            fct_mj = 2.12 * np.log(1 + 0.11 * self.fckj())
        return fct_mj

    def fctkinf(self):
        '''fctkinf - Resistência inferior à tração do concreto (NBR 6118:2023 - 8.2.5)'''
        fctk_inf = 0.7 * self.fctm()
        return fctk_inf

    def fctkinfj(self):
        '''fctkinfj - Resistência inferior à tração do concreto em data inferior aos 28 dias, desde que fckj >= 7MPa (NBR 6118:2023 - 8.2.5)'''
        # HOLD: Implementar aviso para fckj < 7MPa
        fctk_infj = 0.7 * self.fctmj()
        return fctk_infj
                
    def fctksup(self):
        '''fctksup - Resistência superior à tração do concreto (NBR 6118:2023 - 8.2.5)'''
        fctk_sup = 1.3 * self.fctm()
        return fctk_sup

    def fctksupj(self):
        '''fctksupj - Resistência superior à tração do concreto em data inferior aos 28 dias, desde que fckj >= 7MPa (NBR 6118:2023 - 8.2.5)'''
        # HOLD: Implementar aviso para fckj < 7MPa
        fctk_supj = 1.3 * self.fctmj()
        return fctk_supj

    def fcd(self):
        '''fcd - Resistência de cálculo à compressão do concreto (NBR 6118:2023 - 12.3.3)'''
        fc_d = self.fck / self.gama_c
        return fc_d

    def fctd(self):
        '''fcd - Resistência de cálculo à tração do concreto (NBR 6118:2023 - 9.3.2.1)'''
        fctd = self.fctkinf() / self.gama_c
        return fctd

    def Eci(self):
        '''Eci - Módulo de elasticidade ou módulo de deformação tangente inicial do concreto (NBR 6118: 2023 - 8.2.8)'''
        if self.fck <= 50:
            E_ci = self.alfa_e * 5600 * pow(self.fck, 0.5)
        elif self.fck <= 90:
            E_ci = 21.5 * pow(10,3) * self.alfa_e * pow(((self.fck / 10) + 1.25), (1 / 3))
        return E_ci
    
    def Ecij(self):
        '''Eci - Módulo de elasticidade ou módulo de deformação tangente inicial do concreto no instante j (NBR 6118: 2023 - 8.2.8)'''
        if self.dias < 7:
            E_cij = 'Valor não definido para tempo inferior a 7 dias'
        elif self.dias <= 28:
            if self.fck <= 50:
                E_cij = pow((self.fckj() / self.fck), 0.5) * self.Eci()
            elif self.fck <= 90:
                E_cij = pow((self.fckj() / self.fck), 0.3) * self.Eci()
        return E_cij
    
    def Ecs(self):
        '''Ecs - Módulo de deformação secante do concreto (NBR 6118: 2023 - 8.2.8)'''
        alfa_i = 0.8 + (0.2 * self.fck / 80)
        if alfa_i > 1: 
            alfa_1 = 1

        if self.dias < 7:
            E_cs = 'Valor não definido para tempo inferior a 7 dias'
        else:
            E_cs = alfa_i * self.Eci()
        return E_cs

    def sigma_max_c_ato(self):
        '''ELU do concreto protendido no ATO (NBR 6118:2023 - 17.2.4.3.2): Tensão máxima de compressão'''
        if self.fck <= 50:
            sigma_max_c_ato_dias = 0.7 * self.fckj()
        elif self.fck <= 90:
            sigma_max_c_ato_dias = 0.7 * (1 - (self.fckj()-50) / 200)
        return sigma_max_c_ato_dias

    def sigma_max_t_ato(self):
        '''ELU do concreto protendido no ATO (NBR 6118:2023 - 17.2.4.3.2): Tensão máxima de tração'''
        sigma_max_t_ato_dias = 1.2 * self.fctmj()
        return sigma_max_t_ato_dias

    def sigma_max_c_els_qperm(self):
        '''ELS - Limite de tensão de compressão do concreto - Na combinação quase permanente (NBR 6118:2023 - 17.2.4.4.1)'''
        sigma_max_c_els_cqperm = 0.45 * self.fck
        return sigma_max_c_els_cqperm
    
    def sigma_max_c_els_freq(self):
        '''ELS - Limite de tensão de compressão do concreto - Na combinação frequente (NBR 6118:2023 - 17.2.4.4.1)'''
        sigma_max_c_els_cfreq = 0.6 * self.fck
        return sigma_max_c_els_cfreq

    def sigma_max_c_els_rara(self):
        '''ELS - Limite de tensão de compressão do concreto - Na combinação rara (válida só para PROT COMPLETA (nível 3)) (NBR 6118:2023 - 17.2.4.4.1)'''
        sigma_max_c_els_crara = 0.6 * self.fck
        return sigma_max_c_els_crara

    def sigma_max_t_els_f(self):
        '''ELS-F - ELU de formação de fissuras, tensão na qual a seção passa a trabalhar no Estádio II - seção fissurada (NBR 6118:2023 - 17.2.4.4.2)'''
        sigma_max_t_els_f_ = 0.7 * self.alfa_fator * self.fctm() 
        return sigma_max_t_els_f_

    def sigma_max_t_els_d(self):
        '''ELS-D - ELU de descompressão, tensão de tração limite nula (NBR 6118:2023 - 17.2.4.4.2)'''
        sigma_max_t_els_d_ = 0 
        return sigma_max_t_els_d_
        
    def alfav2(self):
        '''alfa,v2 - Parâmetro do concreto utilizado para cálculo de resistências do concreto (V,Rd2, T,Rd2, f,cd1, fcd2, fcd3, etc) (NBR 6118: 17.5.1.5)'''
        alfa_v2 = 1 - (self.fck / 250)
        return alfa_v2
    
    def fcd1(self):
        '''fcd1 - Resistências a compressão do concreto de cálculo de bielas e regiões nodais (NBR 6118:2023 - 22.3.2) - Para bielas prismáticas ou nós CCC'''
        fcd_1 = 0.85 * self.alfav2() * self.fcd()
        return fcd_1

    def fcd2(self):
        '''fcd1 - Resistências a compressão do concreto de cálculo de bielas e regiões nodais (NBR 6118:2023 - 22.3.2) - Para bielas atravessadas por mais de um tirante, ou nós CTT/TTT'''
        fcd_2 = 0.6 * self.alfav2() * self.fcd()
        return fcd_2

    def fcd3(self):
        '''fcd1 - Resistências a compressão do concreto de cálculo de bielas e regiões nodais (NBR 6118:2023 - 22.3.2) - Para bielas atravessadas por um único tirante, ou nós CCT'''
        fcd_3 = 0.72 * self.alfav2() * self.fcd()
        return fcd_3

    def epsilonc2(self):
        '''epsilonc2 - Deformação específica de encurtamento do concreto (no início do patamar plástico e de ruptura), para análises no ELU (NBR 6118:2023 8.2.10.1)'''
        if self.fck <= 50:
            epsilon_c2 = 0.0020
        elif self.fck <= 90:
            epsilon_c2 = 0.0020 + (0.085 / 1000) * pow((self.fck - 50), 0.53)
        return epsilon_c2

    def epsiloncu(self):
        '''epsiloncu - Deformação última de encurtamento do concreto, para análises no ELU (NBR 6118:2023 8.2.10.1)'''
        if self.fck <= 50:
            epsilon_cu = 0.0035
        elif self.fck <= 90:
            epsilon_cu = 0.0026 + (35 / 1000) * pow(((90 - self.fck) / 100), 4)
        return epsilon_cu
    
    def etac(self):
        '''etac - Parâmetros para o cálculo da Tensão-deformação do concreto - Compressão (NBR 6118:2023 8.2.10.1)'''
        if self.fck <= 40:
            eta_c = 1
        elif self.fck > 40:
            eta_c = pow((40 / self.fck), (1/3))
        return eta_c

    def nc(self):
        '''nc - Parâmetros para o cálculo da Tensão-deformação do concreto - Compressão (NBR 6118:2023 8.2.10.1)'''
        if self.fck <= 50:
            n_c= 2   
        elif self.fck >50:
            n_c = 1.4 + 23.4 * pow (((90 - self.fck) / 100) , 4)
        return n_c

    def sigma_c2(self):
        '''sigma_c2 - Tensão no início do patamar plástico - Tensão-deformação do concreto - Compressão (NBR 6118:2023 8.2.10.1)'''
        sigma_c2 = 0.85 * self.etac() * self.fcd()
        return sigma_c2
    
    def sigma_c(self):
        '''sigma_c - tensão imposta no concreto, dado o encurtamente o epsilon_c - Tensão-deformação do concreto - Compressão (NBR 6118:2023 8.2.10.1)'''
        if self.epsilon_c < self.epsilonc2():
            sigma_c = 0.85 * self.etac() * self.fcd() * (1 - (pow(1 -  (self.epsilon_c / self.epsilonc2()), self.nc())))
        else:
            sigma_c = self.sigma_c2()
        return sigma_c

    def epsilon_tu(self):
        '''epsilon_tu - Deformação última - Deformação de tração do concreto (bilinear), para concreto não fissurado (NBR 6118:2023 8.2.10.2)'''
        epsilon_tu = 0.00015
        return epsilon_tu
    
    def epsilon_t2(self):
        '''epsilon_t2 - Deformação que separa o diagrama bilinear (foi adotado fctk como fctk_inf pois considera-se o concreto como não fissurado) - Deformação de tração do concreto (bilinear), para concreto não fissurado (NBR 6118:2023 8.2.10.2)'''
        epsilon_t2 = (0.9 * self.fctkinf()) / self.Eci()
        return epsilon_t2
    
    def sigma_t(self):
        '''sigma_t - Tensão dada uma deformação epsilon_t - Deformação de tração do concreto (bilinear), para concreto não fissurado (NBR 6118:2023 8.2.10.2)'''
        if self.epsilon_t <= self.epsilon_t2():
            sigma_t = self.Eci() * self.epsilon_t
        else:
            mct = (0.1 * self.fctkinf()) / (self.epsilon_tu() - self.epsilon_t2())
            sigma_t = mct * self.epsilon_t    
        return sigma_t

    def massaEspecifica(self):
        '''Massa específica (concreto armado) em tf/m³- (NBR 6118:2023 8.2.2)'''
        mespc = 2.5
        return mespc

    def coefDilatacaoTermica(self):
        '''Coeficiente de dilatação térmica (NBR 6118:2023 8.2.3)'''
        coef_dilatacao_termica = pow(10, -5)
        return coef_dilatacao_termica
    
    def poisson(self):
        '''Coeficiente de poisson (0.2 é um valor válido para tensões menores que 0.5fc e tensões de tração menores que fct) - (NBR 6118:2023 8.2.9)'''
        poisson = 0.2
        return poisson
    
    def Gc(self):
        '''Módulo de elasticidade transversal - (NBR 6118:2023 8.2.9)'''
        G_c = self.Ecs() / 2.4
        return G_c
    
    # Método criado pelo Professor Corsini. 
    def all_methods(self):
        '''all_methods - Métodos disponíveis para o objeto Concreto'''

        dictExport = {
            'fckj': float(self.fckj()),
            'fctmj': float(self.fctmj()),
            'fctkinf': self.fctkinf(),
            'fctkinfj': float(self.fctkinfj()),
            'fctksup': self.fctksup(),
            'fctksupj': float(self.fctksupj()),
            'fcd': self.fcd(),
            'fctd': self.fctd(),
            'Eci': self.Eci(),
            'Ecij': float(self.Ecij()),
            'Ecs': self.Ecs(),
            'taxaMinima': self.taxaMinima(),
            'sigma_max_c_ato': float(self.sigma_max_c_ato()),
            'sigma_max_t_ato': float(self.sigma_max_t_ato()),
            'sigma_max_c_els_qperm': self.sigma_max_c_els_qperm(),
            'sigma_max_c_els_freq': self.sigma_max_c_els_freq(),
            'sigma_max_c_els_rara': self.sigma_max_c_els_rara(),
            'sigma_max_t_els_f': self.sigma_max_t_els_f(),
            'sigma_max_t_els_d': self.sigma_max_t_els_d(),
            'alfav2': self.alfav2(),
            'fcd1': self.fcd1(),
            'fcd2': self.fcd2(),
            'fcd3': self.fcd3(),
            'epsilonc2': self.epsilonc2(),
            'epsiloncu': self.epsiloncu(),
            'etac': self.etac(),
            'nc': self.nc(),
            'sigma_c2': self.sigma_c2(),
            'sigma_c': self.sigma_c(),
            'epsilon_tu': self.epsilon_tu(),
            'epsilon_t2': self.epsilon_t2(),
            'sigma_t': self.sigma_t(),
            'massaEspecifica': self.massaEspecifica(),
            'coefDilatacaoTermica': self.coefDilatacaoTermica(),
            'poisson': self.poisson(),
            'Gc': self.Gc()
        }
        
        return dictExport
    






#############################################################################################################################
###################################        PROPRIEDADE DO AÇO DE ARMADURA PASSIVA         ###################################
#############################################################################################################################
    
class Aco():
    ''' ##INPUTS
    CA___Tipo de aço (relacionado ao fyk), padrão 50

    fi          Diâmetro da barra em mm, padrão 0.5

    eta2        Coeficiente de aderência relacionado ao posicionamento da barra (NBR 6118:2023 item 9.3.1)

    alfa        Correção para a ancoragem dependendo da existência de dobra e/ou barras transversais soldadas (NBR 6118:2023 item 9.4.2.5)

    gama_s      Coeficiente de resistência

    epsilon_s   Deformação de tração do aço (NBR 6118:2023 - 8.3.6)
    '''
    def __init__(self, CA = 50, fi = 5, eta2 = 0.7, alfa = 1, gama_s = 1.15, epsilon_s = 0.002381):
        self.CA = CA
        self.fi = fi
        self.eta2 = eta2
        self.alfa = alfa
        self.gama_s = gama_s
        self.epsilon_s = epsilon_s

    def eta1(self):
        '''eta1 - Relacionado à aderencia - tipo de superfície da barra (NBR 6118:2023 - 8.3.2 - Tabela 8.2) '''
        match self.CA:
            case 50:
                eta_1 = 2.25
            case 25:
                eta_1 = 1.00
            case 60:
                eta_1 = 1.00
        return eta_1

    def eta3(self):
        '''eta3 - Relacionado à aderencia - depende da bitola da barra (NBR 6118:2023 - 9.3.2.1)'''
        if self.fi < 32:
            eta_3 = 1
        else:
            eta_3 = (132 - self.fi)/100
        return eta_3

    def fyk(self):
        '''fyk - Resistência característica ao escoamento do aço da armadura passiva (NBR 6118:2023 - 8.3.6) '''
        match self.CA:
            case 50:
                fyk = 500
            case 25:
                fyk = 250
            case 60:
                fyk = 600
        return fyk

    def fyd(self):
        '''fyd - Resistência de dimensionamento do aço da armadura passiva'''
        fyd = self.fyk() / self.gama_s
        return fyd

    def pinoDobramento(self):
        '''pinoDobramento - Diâmetro do pino de dobramento para ganchos de armaduras longitudinais de tração (NBR 6118:2023 - 9.4.2.3)'''
        match self.CA:
            case 50:
                if self.fi <= 20:
                    fi_pino_dobramento = 5 * self.fi
                elif self.fi > 20:
                    fi_pino_dobramento = 8 * self.fi
            case 25:
                if self.fi <= 20:
                    fi_pino_dobramento = 4 * self.fi
                elif self.fi > 20:
                    fi_pino_dobramento = 5 * self.fi
            case 60:
                if self.fi <= 20:
                    fi_pino_dobramento = 6 * self.fi
                elif self.fi > 20:
                    fi_pino_dobramento = "Não aplicável"
        return fi_pino_dobramento    

    def gancho180(self):
        '''gancho180 - Trecho reto dos ganchos das armaduras de tração (NBR 6118:2023 - 9.4.2.3) (em cm) (foi acrescentado a bitola da barra para considerar o comprimento total da dobra da barra)'''
        gancho_180 = self.pinoDobramento() + 2 * self.fi
        return gancho_180

    def gancho45(self):
        '''gancho45 - Trecho reto dos ganchos das armaduras de tração (NBR 6118:2023 - 9.4.2.3) (em cm) (foi acrescentado a bitola da barra para considerar o comprimento total da dobra da barra)'''
        gancho_45 = 4 * self.fi + 1.5 * self.fi
        return gancho_45    

    def gancho90(self):
        '''gancho90 - Trecho reto dos ganchos das armaduras de tração (NBR 6118:2023 - 9.4.2.3) (em cm) (foi acrescentado a bitola da barra para considerar o comprimento total da dobra da barra)'''
        gancho_90 = 8 * self.fi + 1.5 * self.fi
        return gancho_90

    def massaEspecifica(self):
        '''massaEspecifica - Massa específica (NBR 6118:2023 - 8.3.3)'''
        massa_especifica = 7850     
        return massa_especifica
    
    def coefDilatacaoTermica(self):
        '''coefDilatacaoTermica - Coeficiente de dilatação térmica (NBR 6118:2023 - 8.3.4)'''
        coef_dilatacao_termica = pow(10, -5)
        return coef_dilatacao_termica

    def Es(self):
        '''Es - Módulo de elasticidade (NBR 6118:2023 - 8.3.5)'''
        E_s = 210000
        return E_s

    def area(self):
        '''area - Área (cm²) da barra'''
        As_barra = math.pi * pow (self.fi / 20, 2) 
        return As_barra

    def massaNominal(self):
        '''massaNominal - Massa nominal (linear) (kg/m)'''
        massa_nominal = self.massaEspecifica() * pow(10, -4) * self.area()
        return massa_nominal

    def epsilon_s2(self):
        '''epsilon_s2 - Deformação no início do escoamento - Tensão-Deformação do aço (NBR 6118:2023 - 8.3.6)'''
        epsilon_s2 = self.fyk() / self.Es()
        return epsilon_s2

    def sigma_s(self):
        '''sigma_s - Tensão dada a deformação epsilon_s - Tensão-Deformação do aço (NBR 6118:2023 - 8.3.6)'''
        if self.epsilon_s <= self.epsilon_s2():
            sigma_s = self.Es() * self.epsilon_s
        else:
            sigma_s = self.fyk()      
        return sigma_s


# EXEMPLO DE USO
# conc30 = Concreto(fck=30, # UNICO PARÂMETRO OBRIGATÓRIO
#                   dias = 28, 
#                   gama_c = 1.4, 
#                   alfa_e = 0.8, 
#                   alfa_fator = 1.5, 
#                   epsilon_c = 0.002, 
#                   epsilon_t = 0.00015
#                 )

# print(conc30.all_methods())