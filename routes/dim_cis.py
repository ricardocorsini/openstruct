"""
Script desenvolvido no treinamento de Python para Engenharia Estrutural. 
Autor: Ricardo Corsini de Carvalho (Professor)
github: https://github.com/ricardocorsini
"""

import numpy as np
import pandas as pd

class Beam:

    beamsCreated = []

    def __init__(self, name, bw, h, Vk, gama_c, gama_c2, fywk, gama_s, fck, stirrupLeg):
        self.name = name
        self.bw = bw
        self.h = h
        self.Vk = Vk
        self.gama_c = gama_c    #minoração do fck
        self.gama_c2 = gama_c2  #majoração do Vk
        self.fywk = fywk
        self.gama_s = gama_s
        self.fck = fck
        self.stirrupLeg = stirrupLeg
        self.concrete_properties()

        self.d = self.h - 5
        self.Vd = self.Vk * self.gama_c2

        Beam.beamsCreated.append(self)

    def __str__(self):
        return f'{self.name} - {self.bw} X {self.h}'
        
    def concrete_properties(self):
        self.fcd = self.fck / self.gama_c
        self.fywd = self.fywk / self.gama_s
        self.fctm = 0.3 * pow(self.fck, 2 / 3)
        self.fctk_inf = 0.7 * self.fctm
        self.fctd = self.fctk_inf / self.gama_c

        dictExport = {
            'fck (MPa)': self.fck,
            'fcd (MPa)': self.fcd,
            'fywd (MPa)': self.fywd,
            'fctm (MPa)': self.fctm,
            'fctk_inf (MPa)': self.fctk_inf,
            'fctd (MPa)': self.fctd
        }

        return dictExport


    def compressed_cis(self):

        alphaV2 = 1 - (self.fck / 250)
        vrd2 = 0.27 * alphaV2 * (self.fcd / 10) * self.bw * self.d

        if self.Vd <= vrd2:
            statusCompressed = 'ok'
        else:
            statusCompressed = 'disapproved'

        dictExport = {
            'alphaV2': alphaV2,
            'Vrd2 (kN)': vrd2,
            'Vd (kN)': self.Vd,
            'status': statusCompressed
        }

        return dictExport

    def tension_cis(self):
        Vc = 0.6 * (self.fctd / 10) * self.bw * self.d
        asw_min_cm = 0.2 * self.fctm * (self.bw / self.fywk)
        asw_min_m = asw_min_cm * 100
        Vsw_min = asw_min_cm * 0.9 * self.d * (self.fywd / 10)
        vrd3_min = Vsw_min + Vc

        if self.Vd <= vrd3_min:
            asw_adot = asw_min_m
            statusTension = 'aws = armadura minima'
        else:
            asw_adot = 100 * (self.Vd - Vc) / (0.9 * self.d * (self.fywd / 10))
            statusTension = 'asw = acima da minima'
        
        dictExport = {
            'Vc (kN)': Vc,
            'asw_min (cm2/cm)': asw_min_cm,
            'asw_min (cm2/m)': asw_min_m,
            'Vsw_min (kN)': Vsw_min,
            'Vrd3_min (kN)': vrd3_min,
            'StatusTension': statusTension,
            'asw_adot (cm2/m)': asw_adot
            
        }

        return dictExport
    
    def detailing(self):
        asw_adot = Beam.tension_cis(self)['asw_adot (cm2/m)']

        listDiameter = np.array([5.0, 6.3, 8.0, 10.0, 12.5, 16.0, 20.0, 25.0, 32.0, 40.0])
        areas = self.stirrupLeg * np.pi * pow(listDiameter / 10, 2) / 4

        spacing = (areas / asw_adot) * 100
        spacing_round = np.floor(spacing)

        dictExport = {
            'Diameter (mm)': list(listDiameter),
            'Spacing (cm)': list(spacing_round)
        }

        return dictExport
    
    def list_beam():
        for beam in Beam.beamsCreated:
            print(beam)

    def results_dim_cis(self):
        results_concrete = Beam.concrete_properties(self)
        results_compressed_cis = Beam.compressed_cis(self)
        results_tension = Beam.tension_cis(self)
        results_detailing = Beam.detailing(self)

        dictExport = {
            'results_concrete': results_concrete,
            'results_compressed_cis': results_compressed_cis,
            'results_tension': results_tension,
            'results_detailing': results_detailing
        }

        return dictExport
