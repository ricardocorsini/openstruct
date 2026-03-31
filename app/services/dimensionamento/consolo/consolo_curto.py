import math
import json
from dataclasses import dataclass, asdict
from typing import Dict, Any, List

@dataclass
class ConsoloCurto:
    nome: str
    bw: float          # cm
    h: float           # cm
    d_linha: float     # cm
    dist_a: float      # cm
    vk: float          # kN
    hk: float          # kN
    fck: float         # MPa
    fywk: float        # MPa
    gama_c: float = 1.4
    gama_s: float = 1.15
    gama_f: float = 1.4

    # Limites normativos para inclinação da biela (30° a 60°)
    COTG_MIN: float = 0.577
    COTG_MAX: float = 1.732
    LIMITE_DUCTILIDADE: float = 0.45

    # --- PROPRIEDADES (Valores de Cálculo) ---
    @property
    def d(self) -> float: 
        return self.h - self.d_linha

    @property
    def vd(self) -> float: 
        return self.vk * self.gama_f

    @property
    def hd(self) -> float: 
        # NBR 6118: Força horizontal mínima de 20% da vertical
        hd_calc = self.hk * self.gama_f
        return max(hd_calc, 0.2 * self.vd)

    @property
    def fcd(self) -> float: 
        return (self.fck / 10) / self.gama_c

    @property
    def fcd1(self) -> float:
        # Tensão limite na biela comprimida (fcd1 = 0,85 * alpha_v2 * fcd)
        alpha_v2 = 1 - (self.fck / 250)
        return 0.85 * alpha_v2 * self.fcd

    @property
    def fywd(self) -> float: 
        return (self.fywk / 10) / self.gama_s

    # --- CÁLCULOS TÉCNICOS ---
    def calcular_geometria_biela(self) -> Dict[str, Any]:
        """Calcula os parâmetros do modelo de bielas e tirantes e verifica ductilidade."""
        dist_e = (self.hd / self.vd) * self.d_linha 
        dist_x_aux = self.vd / (self.bw * self.fcd1) # x auxiliar para cálculo de l
        dist_l = self.dist_a + dist_e + (dist_x_aux / 2)
        
        try:
            # Equação de equilíbrio para encontrar a profundidade do bloco (y)
            termo_raiz = math.pow(self.d, 2) - 2 * dist_l * dist_x_aux
            dist_y = self.d - math.sqrt(termo_raiz)
            dist_z = self.d - (dist_y / 2)
            cotg_teta = dist_l / dist_z
            
            # Verificações
            biela_ok = self.COTG_MIN <= cotg_teta <= self.COTG_MAX
            
            # Verificação de Ductilidade solicitada: y / (0.8 * d) <= 0.45
            razao_xd = dist_y / (0.8 * self.d)
            ductilidade_ok = razao_xd <= self.LIMITE_DUCTILIDADE

            return {
                "dist_e": dist_e,
                "dist_x_aux": dist_x_aux,
                "dist_l": dist_l,
                "dist_y": dist_y,
                "dist_z": dist_z,
                "cotg_teta": cotg_teta,
                "razao_xd": razao_xd,
                "biela_ok": biela_ok,
                "ductilidade_ok": ductilidade_ok
            }
        except ValueError:
            return {"erro": "Falha geométrica: Seção insuficiente (Raiz negativa)", "biela_ok": False, "ductilidade_ok": False}

    def calcular_armaduras(self) -> Dict[str, float]:
        """Calcula armadura principal (tirante) e de costura."""
        geom = self.calcular_geometria_biela()
        if "erro" in geom: 
            return {"as_tirante": 0.0, "as_min": 0.0, "f_tirante": 0.0, "as_costura": 0.0}

        # Força no tirante principal
        f_tirante = self.vd * geom['cotg_teta'] + self.hd
        as_calculado = f_tirante / self.fywd
        
        # Armadura mínima NBR 6118
        rho_min = 0.04 * (self.fck / self.fywk)
        as_min = rho_min * self.bw * self.d
        
        as_final_tirante = max(as_calculado, as_min)
        
        # Armadura de costura (estribos horizontais) - 40% da principal
        as_costura = 0.40 * as_final_tirante

        return {
            "f_tirante": f_tirante,
            "as_tirante": as_final_tirante,
            "as_min": as_min,
            "as_costura": as_costura,
            "detalhamento_tirante": self.sugerir_detalhamento(as_final_tirante, "tirante"),
            "detalhamento_costura": self.sugerir_detalhamento(as_costura, "costura")
        }

    # --- EXPORTAÇÃO JSON (PARA API) ---
    def gerar_json(self) -> str:
        return json.dumps(self.gerar_resultado(), indent=4, ensure_ascii=False)

    # --- GERAÇÃO DA MEMÓRIA DE CÁLCULO (TXT) ---
    def gerar_memoria_calculo(self) -> str:
        geom = self.calcular_geometria_biela()
        arm = self.calcular_armaduras()
        
        memoria = [
            f"{'MEMÓRIA DE CÁLCULO: ' + self.nome :^60}",
            f"{'Dimensionamento de Consolo Curto (NBR 6118)' :^60}",
            "="*60,
            "\n1. DADOS DE ENTRADA (CARACTERÍSTICOS)",
            f"   Seção: bw = {self.bw:.2f} cm | h = {self.h:.2f} cm | d' = {self.d_linha:.2f} cm",
            f"   Geometria: a = {self.dist_a:.2f} cm",
            f"   Cargas: Vk = {self.vk:.2f} kN | Hk = {self.hk:.2f} kN",
            f"   Materiais: fck = {self.fck:.2f} MPa | fywk = {self.fywk:.2f} MPa",
            f"   Segurança: γc = {self.gama_c} | γs = {self.gama_s} | γf = {self.gama_f}",
            
            "\n2. PARÂMETROS DE CÁLCULO E RESISTÊNCIAS",
            f"   Altura útil (d): {self.d:.2f} cm",
            f"   Esforço Vd (majorado): {self.vd:.2f} kN",
            f"   Esforço Hd (mín 20% Vd): {self.hd:.2f} kN",
            f"   Resistência fcd: {self.fcd:.4f} kN/cm²",
            f"   Limite Biela fcd1: {self.fcd1:.4f} kN/cm²",
            f"   Resistência fywd: {self.fywd:.2f} kN/cm²",
            
            "\n3. ANÁLISE GEOMÉTRICA DO MODELO (BIELA/TIRANTE)"
        ]

        if "erro" in geom:
            memoria.append(f"   >>> ERRO CRÍTICO: {geom['erro']}")
        else:
            memoria.extend([
                f"   Excentricidade adicional (e): {geom['dist_e']:.2f} cm",
                f"   Prof. bloco compressão inicial (x_aux): {geom['dist_x_aux']:.2f} cm",
                f"   Distância horizontal total (l): {geom['dist_l']:.2f} cm",
                f"   Prof. efetiva da biela (y): {geom['dist_y']:.2f} cm",
                f"   Braço de alavanca (z): {geom['dist_z']:.2f} cm",
                f"   Inclinação da biela (cotg θ): {geom['cotg_teta']:.3f}",
                f"   Verificação da Biela: {'APROVADA' if geom['biela_ok'] else 'REPROVADA'}",
                "\n4. VERIFICAÇÃO DE DUCTILIDADE",
                f"   Razão x/d (y / 0.8*d): {geom['razao_xd']:.3f}",
                f"   Limite de Ductilidade: {self.LIMITE_DUCTILIDADE}",
                f"   Status Ductilidade: {'APROVADA' if geom['ductilidade_ok'] else 'FALHA (Seção super-armada)'}"
            ])

        memoria.extend([
            "\n5. DIMENSIONAMENTO DE ARMADURAS",
            f"   Força de Tração no Tirante (Fs): {arm['f_tirante']:.2f} kN",
            f"   Área de Aço Principal (As): {arm['as_tirante']:.2f} cm² (inclui As,min)",
            f"   Área de Aço Costura (As_cost = 0.4*As): {arm['as_costura']:.2f} cm²",
            f"   Referência As,mínimo: {arm['as_min']:.2f} cm²",
            "\n" + "="*60
        ])

        # --- Seção de Detalhamento na Memória ---
        memoria.append("\n5. SUGESTÃO DE DETALHAMENTO COMERCIAL (TODAS AS BITOLAS)")
        
        memoria.append("   Tirante Principal (Laços de 2 pernas):")
        for sug in arm['detalhamento_tirante']:
            memoria.append(f"    • {sug['texto']}")
            
        memoria.append("\n   Armadura de Costura (Estribos de 2 pernas):")
        for sug in arm['detalhamento_costura']:
            memoria.append(f"    • {sug['texto']}")
            
        memoria.append("\n" + "="*60)

        texto_final = "\n".join(memoria)
        
        # Salva o arquivo txt
        filename = f"Memoria_{self.nome}.txt"
        with open(filename, "w", encoding="utf-8") as f:
            f.write(texto_final)
        
        return texto_final
    
    def sugerir_detalhamento(self, as_alvo: float, tipo: str = "tirante") -> List[Dict[str, Any]]:
        """
        Converte cm² em sugestões para todas as bitolas, considerando 2 pernas por unidade.
        """
        bitolas = {
            6.3: 0.312, 8.0: 0.503, 10.0: 0.785, 
            12.5: 1.227, 16.0: 2.011, 20.0: 3.142
        }
        
        sugestoes = []
        # Define o rótulo com base no tipo
        rotulo = "laços" if tipo == "tirante" else "estribos"
        
        for phi, area_unit in bitolas.items():
            n_pernas = math.ceil(as_alvo / area_unit)
            n_unidades = math.ceil(n_pernas / 2)

            sugestoes.append({
                "bitola": phi,
                "texto": f"Bitola {phi} = {n_unidades} {rotulo} necessários",
            })

        return sugestoes
    
    def gerar_resultado(self) -> Dict[str, Any]:
        geom = self.calcular_geometria_biela()
        arm = self.calcular_armaduras()

        return {
            "identificacao": self.nome,
            "entradas": {
                "nome": self.nome,
                "bw": self.bw,
                "h": self.h,
                "d_linha": self.d_linha,
                "dist_a": self.dist_a,
                "vk": self.vk,
                "hk": self.hk,
                "fck": self.fck,
                "fywk": self.fywk,
                "gama_c": self.gama_c,
                "gama_s": self.gama_s,
                "gama_f": self.gama_f,
            },
            "propriedades_calculo": {
                "d_cm": self.d,
                "vd_kn": self.vd,
                "hd_kn": self.hd,
                "fcd_kn_cm2": self.fcd,
                "fcd1_kn_cm2": self.fcd1,
                "fywd_kn_cm2": self.fywd
            },
            "geometria_biela": geom,
            "armaduras": arm,
            "verificacoes_finais": {
                "biela_status": "OK" if geom.get("biela_ok") else "FALHA",
                "ductilidade_status": "OK" if geom.get("ductilidade_ok") else "FALHA"
            }
        }

# --- EXECUÇÃO ---
if __name__ == "__main__":
    consolo = ConsoloCurto(
        nome='C1', bw=40, h=65, d_linha=5, 
        dist_a=30, vk=571.42, hk=92.85, 
        fck=40, fywk=500
    )

    # 1. Gera e imprime a Memória detalhada (e salva TXT)
    print(consolo.gerar_memoria_calculo())
    
    # 2. Imprime o JSON completo para validação de API
    print("\n--- JSON EXPORT (API READY) ---")
    print(consolo.gerar_json())