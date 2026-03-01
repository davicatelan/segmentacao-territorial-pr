# -*- coding: utf-8 -*-
"""
Segmentação territorial de municípios do Paraná
PCA (Varimax) + K-Means + ANOVA

Autor: Davi
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
# PCA (3 FATORES + VARIMAX)
# =========================

fa = FactorAnalyzer(n_factors=3, method="principal", rotation="varimax")
fa.fit(base_pca_pad)

# =========================
# VARIÂNCIA EXPLICADA
# =========================

variance = fa.get_factor_variance()

tabela_variancia = pd.DataFrame(variance).T
tabela_variancia.columns = ["Autovalor", "Variância Explicada", "Variância Acumulada"]
tabela_variancia.index = ["Fator 1", "Fator 2", "Fator 3"]

print("\nVariância por Fator")
print(tabela_variancia)

# Cargas fatoriais
loadings = pd.DataFrame(
    fa.loadings_,
    index=base_pca_pad.columns,
    columns=["Fator 1", "Fator 2", "Fator 3"]
)

print("\nCargas Fatoriais")
print(loadings)

# Escores fatoriais
fatores = pd.DataFrame(
    fa.transform(base_pca_pad),
    columns=["Fator 1", "Fator 2", "Fator 3"]
)

# =========================
# CLUSTERIZAÇÃO
# =========================

fatores_pad = fatores.apply(zscore, ddof=1)

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

# Modelo final (3 clusters)
kmeans_final = KMeans(n_clusters=3, random_state=100, n_init=20)
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
# EXPORTAÇÃO
# =========================

base_analise.to_csv("Base_clusters.txt", sep=";", index=False, encoding="utf-8-sig")

print("\nArquivo 'Base_clusters.txt' exportado com sucesso.")