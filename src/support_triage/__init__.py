"""Triage automatisé des demandes de support d'un ERP Odoo.

Le paquet expose :
  - `schema`         : le contrat de sortie typé (Pydantic) et les énumérations métier
  - `dataset`        : chargement du jeu de tickets annotés
  - `baseline`       : classifieur par règles, servant de ligne de base et de repli
  - `prompt`         : assemblage du prompt à partir des règles et des exemples
  - `llm_classifier` : classifieur LangChain à sortie structurée
  - `triage`         : orchestration, seuil de confiance et escalade humaine
  - `metrics`        : exactitude, F1 macro, confusions et calibration
"""

__version__ = "0.1.0"
