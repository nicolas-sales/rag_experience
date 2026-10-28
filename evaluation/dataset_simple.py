# Même dataset que dataset.py (mêmes réponses, même ordre),
# mais avec des questions courtes, comme un utilisateur les tape dans Streamlit.

import pandas as pd

def build_dataset():

    data = [
        {
            "question": "Davidson Consulting c'est quoi ?",
            "reference": "Davidson Consulting est un acteur du conseil en management et en expertises technologiques.",
            "reference_pages": [5]
        },
        {
            "question": "Quelle part des compétences liée au numérique ?",
            "reference": "70 % des compétences des consultants sont liées au secteur numérique.",
            "reference_pages": [5]
        },
        {
            "question": "Année de création de DUTLER ?",
            "reference": "2005.",
            "reference_pages": [6]
        },
        {
            "question": "Première certification B Corp en quelle année ?",
            "reference": "2018.",
            "reference_pages": [6, 9]
        },
        {
            "question": "Quels sont les trois piliers d'impact ?",
            "reference": "L'impact social, l'impact sociétal et l'impact environnemental.",
            "reference_pages": [7]
        },
        {
            "question": "Quels sont les quatre axes de la stratégie Impact ?",
            "reference": "Mesurer, réduire, augmenter et partager.",
            "reference_pages": [7]
        },
        {
            "question": "Quelles sont les certifications auditées ?",
            "reference": "B Corp, ISO 9001:2015, ISO/IEC 27001:2022 et Qualiopi.",
            "reference_pages": [9]
        },
        {
            "question": "Note EcoVadis 2025 ?",
            "reference": "74/100, avec une médaille Silver.",
            "reference_pages": [9]
        },
        {
            "question": "Qui est dans la Direction Impact ?",
            "reference": "Maëliss Delacroix, Océane Serpin et Thomas Tailhandier.",
            "reference_pages": [10]
        },
        {
            "question": "Depuis quand les missions sont évaluées selon les ODD ?",
            "reference": "Depuis 2022.",
            "reference_pages": [13]
        },
        {
            "question": "Combien de nouvelles missions ODD en 2022 ?",
            "reference": "52 nouvelles missions ODD.",
            "reference_pages": [14]
        },
        {
            "question": "Quel est le stock actif de missions ODD en 2022 ?",
            "reference": "60 missions ODD actives.",
            "reference_pages": [14]
        },
        {
            "question": "Quel est le CA annuel associé pour 2023 ?",
            "reference": "19 215 k€.",
            "reference_pages": [14]
        },
        {
            "question": "CA des missions ODD en 2025 ?",
            "reference": "22,7 millions d'euros, soit 7,7 % du chiffre d'affaires de Davidson en 2025.",
            "reference_pages": [14]
        },
        {
            "question": "Quelle est la mission de redirection écologique de Framatome ?",
            "reference": "Une adaptation à un scénario +4,5°C : accompagnement à la conception d'un plan d'adaptation au changement climatique, application de la méthodologie OCARA, collecte de données environnementales et techniques pour un site type, études de résilience actuelles et futures et identification des risques associés.",
            "reference_pages": [16]
        },
        {
            "question": "Quelle est la mission de redirection écologique chez Decathlon ?",
            "reference": "Davidson a participé à l'écoconception du catalogue de Decathlon, notamment à la définition des leviers de réduction des impacts environnementaux des vélos et à la gouvernance des données nécessaires au calcul de l'impact des produits.",
            "reference_pages": [16]
        },
        {
            "question": "Quelles mesures pour la mobilité domicile-travail ?",
            "reference": "Proposer le télétravail lorsque cela est possible, encourager les mobilités durables avec le Forfait Mobilité Durable ou une aide spécifique, et proposer par exemple le prêt temporaire d'un vélo.",
            "reference_pages": [17]
        },
        {
            "question": "Quel est l'engagement d'ancrage local ?",
            "reference": "Plus de 80 % des missions, pour un objectif d'au moins 75 %.",
            "reference_pages": [18]
        },
        {
            "question": "Quels sont les principes de la satisfaction client ?",
            "reference": "L'excellence opérationnelle, la transparence relationnelle et l'amélioration continue.",
            "reference_pages": [19]
        },
        {
            "question": "Combien de femmes en 2025 et quel pourcentage ?",
            "reference": "693 femmes, soit 30 % de l'effectif global.",
            "reference_pages": [24]
        },
        {
            "question": "Quel est le taux d'emploi handicap en 2025 ?",
            "reference": "1,8 %.",
            "reference_pages": [25]
        },
        {
            "question": "Résultats Great Place To Work 2024 ?",
            "reference": "Trust Index de 83/100 et perception globale de 87/100.",
            "reference_pages": [9, 29]
        },
        {
            "question": "SoliDav 2025 : combien de salariés engagés et d'heures données ?",
            "reference": "283 salariés engagés et 1 782 heures données.",
            "reference_pages": [34, 36, 75, 80]
        },
        {
            "question": "SoliDav 2025 : combien de missions et d'associations ?",
            "reference": "563 missions et 74 associations.",
            "reference_pages": [36, 75, 80]
        },
        {
            "question": "Quel est le bilan carbone 2025 ?",
            "reference": "7 590 tCO2e, dont 560 tCO2e pour les scopes 1 et 2 et 7 030 tCO2e pour le scope 3.",
            "reference_pages": [44]
        },
        {
            "question": "Objectif SBTi des scopes 1 et 2 ?",
            "reference": "Une réduction absolue de 50,4 % des émissions des scopes 1 et 2 par rapport à 2022.",
            "reference_pages": [45]
        },
        {
            "question": "Objectif énergie renouvelable 2030 ?",
            "reference": "Atteindre 100 % d'énergie renouvelable en 2030.",
            "reference_pages": [45]
        },
        {
            "question": "Quelle est la règle sur la confidentialité des données ?",
            "reference": "Chaque collaborateur doit protéger la confidentialité des informations appartenant à Davidson ou à des tiers, ne les transmettre que dans un cadre professionnel légitime et prévenir le délit d'initié ainsi que la divulgation d'informations privilégiées.",
            "reference_pages": [54]
        },
        {
            "question": "Combien est reversé chaque année pour les Droits Humains ?",
            "reference": "10 000 euros par an.",
            "reference_pages": [55]
        },
        {
            "question": "Quels sont les trois premiers axes Right Tech ?",
            "reference": "Mesurer et piloter les impacts numériques ; réduire les externalités négatives par l'écoconception et la sobriété ; augmenter les externalités positives grâce aux contributions collectives et aux outils numériques à impact.",
            "reference_pages": [58]
        },

        # --- Réponses lisibles seulement dans une image (graphique, logo) ---
        {
            "question": "Émissions scopes 1 et 2 en 2023 ?",
            "reference": "936 tCO2e.",
            "reference_pages": [45]
        },
        {
            "question": "Émissions scope 3 en 2024 ?",
            "reference": "6 476 tCO2e.",
            "reference_pages": [45]
        },

        # --- Réponse absente du document : le RAG doit le dire ---
        {
            # "Networks" n'apparaît que dans une infographie, sans chiffre
            "question": "Quelle part de l'activité pour Networks ?",
            "reference": "Cette information n'est pas indiquée dans le document.",
            "reference_pages": [5]
        }
    ]


    return pd.DataFrame(data)


if __name__ == "__main__":

    from pathlib import Path

    df = build_dataset()

    output_path = Path(__file__).resolve().parent / "dataset_simple.csv"

    df.to_csv(
        output_path,
        index=False,
        encoding="utf-8-sig"
    )

    print(df.to_string(index=False))
    print(f"\nDataset sauvegardé : {output_path}")
