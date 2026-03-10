# -*- coding: utf-8 -*-
"""
Segmentação territorial de municípios do Paraná
PCA (Varimax) + K-Means + ANOVA

Autor: Davi
"""

"""
Variáveis utilizadas no modelo:

CrescimentoEmprego -> crescimento relativo do emprego industrial
EmpregoIND -> participação do emprego industrial no total de empregos
MassaSalarial -> massa salarial industrial per capita
PopJovem -> participação da população de 15 a 24 anos
OfertaTecnica -> razão entre matrículas técnicas e população jovem
"""

# =========================
# IMPORTAÇÃO DE PACOTES
# =========================

import pandas as pd
from scipy.stats import zscore
from factor_analyzer import FactorAnalyzer
from factor_analyzer.factor_analyzer import calculate_bartlett_sphericity
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
import pingouin as pg
import matplotlib.pyplot as plt
import seaborn as sns
import warnings

warnings.filterwarnings("ignore")

# =========================
# LEITURA DA BASE
# =========================

base = pd.read_excel("data/Projetos/Base.xlsx")

if "Municipio" not in base.columns:
    raise ValueError("A base precisa conter a coluna 'Municipio'.")
    
# =========================
# TRATAMENTO DE OUTLIERS
# =========================
# Crescimento muito extremo pode ocorrer em municípios com base industrial pequena.
# Para reduzir a influência de outliers, o crescimento foi truncado no intervalo [-1, 1].

base["CrescimentoEmprego"] = base["CrescimentoEmprego"].clip(-1,1)

print("\nDistribuição após tratamento")
print(base["CrescimentoEmprego"].describe())

# =========================
# PREPARAÇÃO PARA PCA
# =========================

base_pca = base.drop(columns=["Municipio"], errors="ignore")
base_pca = base_pca.apply(pd.to_numeric, errors="coerce")

if base_pca.isna().sum().sum() > 0:
    raise ValueError("Existem valores ausentes. Trate antes de rodar o modelo.")

base_pca_pad = base_pca.apply(zscore, ddof=1)

# =========================
# MATRIZ DE CORRELAÇÃO
# =========================

corr = base_pca_pad.corr()

plt.figure(figsize=(10,6))
sns.heatmap(corr, annot=True, cmap="coolwarm", center=0)
plt.title("Matriz de Correlação")
plt.show()

# =========================
# TESTE DE BARTLETT
# =========================

bartlett, p_value = calculate_bartlett_sphericity(base_pca_pad)

print("Teste de Bartlett")
print("Qui²:", round(bartlett,2))
print("p-valor:", round(p_value,6))

# =========================
# ANÁLISE FATORIAL (PCA + VARIMAX)
# =========================

# 1) Modelo "bruto" (sem rotação) -> usado para decisão do nº de fatores
fa_raw = FactorAnalyzer(n_factors=3, method="principal", rotation=None)
fa_raw.fit(base_pca_pad)

variance_raw = fa_raw.get_factor_variance()
tabela_variancia_raw = pd.DataFrame(variance_raw).T
tabela_variancia_raw.columns = ["Autovalor", "Variância Explicada", "Variância Acumulada"]
tabela_variancia_raw.index = ["Fator 1", "Fator 2", "Fator 3"]

print("\nVariância por Fator (sem rotação) - usada para decisão")
print(tabela_variancia_raw.round(4))

# 2) Modelo rotacionado (Varimax) -> usado para interpretação dos fatores
fa_rot = FactorAnalyzer(n_factors=3, method="principal", rotation="varimax")
fa_rot.fit(base_pca_pad)

variance_rot = fa_rot.get_factor_variance()
tabela_variancia_rot = pd.DataFrame(variance_rot).T
tabela_variancia_rot.columns = ["Autovalor", "Variância Explicada", "Variância Acumulada"]
tabela_variancia_rot.index = ["Fator 1", "Fator 2", "Fator 3"]

print("\nVariância por Fator (com Varimax) - mesma variância total, redistribuída")
print(tabela_variancia_rot.round(4))

# =========================
# CARGAS FATORIAIS (ROTACIONADAS)
# =========================

loadings = pd.DataFrame(
    fa_rot.loadings_,
    index=base_pca_pad.columns,
    columns=["Fator 1", "Fator 2", "Fator 3"]
)

print("\nCargas Fatoriais (originais)")
print(loadings.round(3))

# =========================
# ESCORES FATORIAIS
# =========================

fatores = pd.DataFrame(
    fa_rot.transform(base_pca_pad),
    columns=["Fator 1", "Fator 2", "Fator 3"]
)

# =========================
# CLUSTERIZAÇÃO
# =========================

# 1) Padroniza escores fatoriais 

fatores_pad = fatores.apply(zscore, ddof=1)

# 2) Avaliação de k: inércia, silhueta e tamanho dos clusters

# Elbow
inercia = []
for k in range(1,11):
    kmeans = KMeans(n_clusters=k, random_state=100, n_init=20)
    kmeans.fit(fatores_pad)
    inercia.append(kmeans.inertia_)

plt.plot(range(1,11), inercia, marker="o")
plt.title("Método Elbow")
plt.xlabel("Número de Clusters")
plt.ylabel("Inércia")
plt.show()

# Silhueta
silhueta = []
for k in range(2,11):
    kmeans = KMeans(n_clusters=k, random_state=100, n_init=20)
    labels = kmeans.fit_predict(fatores_pad)
    silhueta.append(silhouette_score(fatores_pad, labels))

plt.plot(range(2,11), silhueta, marker="o")
plt.title("Método da Silhueta")
plt.xlabel("Número de Clusters")
plt.ylabel("Silhueta Média")
plt.show()

# 3) Tamanho dos clusters para k candidatos (ajuda a validar a escolha)

k_candidatos = [3, 4, 5]

print("\nTamanho dos clusters (validação por k)")
for k in k_candidatos:
    km = KMeans(n_clusters=k, random_state=100, n_init=20, init="k-means++")
    labels = km.fit_predict(fatores_pad)
    counts = pd.Series(labels).value_counts().sort_index()

    print(f"\n{k} clusters:")
    print(counts)

# 4) Modelo final (definição do k escolhido)
k_final = 4

kmeans_final = KMeans(n_clusters=k_final, random_state=100, n_init=20, init="k-means++")
base["Cluster"] = kmeans_final.fit_predict(fatores_pad)

# =========================
# ANOVA
# =========================

base_analise = pd.concat([base, fatores], axis=1)

print("\nANOVA Fator 1")
print(pg.anova(dv="Fator 1", between="Cluster", data=base_analise))

print("\nANOVA Fator 2")
print(pg.anova(dv="Fator 2", between="Cluster", data=base_analise))

print("\nANOVA Fator 3")
print(pg.anova(dv="Fator 3", between="Cluster", data=base_analise))

# =========================
# >>> ADICIONADO: PERFIL DOS CLUSTERS (INTERPRETAÇÃO)
# =========================

# 1) Média dos fatores por cluster
print("\nMédia dos fatores por cluster")
print(base_analise.groupby("Cluster")[["Fator 1", "Fator 2", "Fator 3"]].mean().round(3))

# 2) Média das variáveis originais por cluster 
print("\nMédia das variáveis originais por cluster")
print(base.groupby("Cluster")[base_pca.columns].mean().round(3))

# 3) Municípios por cluster 
print("\nTamanho dos clusters")
print(base["Cluster"].value_counts().sort_index())

# =========================
# EXPORTAÇÃO
# =========================

base_analise.to_csv("resultados_clusters.csv", sep=";", index=False, encoding="utf-8-sig")
