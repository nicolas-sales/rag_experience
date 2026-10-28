# Même dataset que dataset.py (mêmes réponses, même ordre),
# mais chaque question reprend les mots du PDF.
# Comparer les deux montre si un échec vient de la recherche Qdrant
# (mots différents du PDF) ou de l'extraction.

import pandas as pd

def build_dataset():

    data = [
        {
            "question": "Comment Davidson Consulting se positionne-t-il ?",
            "reference": "Davidson Consulting est un acteur du conseil en management et en expertises technologiques.",
            "reference_pages": [5]
        },
        {
            "question": "Quelle part des compétences des consultant(e)s de Davidson est liée au secteur numérique ?",
            "reference": "70 % des compétences des consultants sont liées au secteur numérique.",
            "reference_pages": [5]
        },
        {
            "question": "En quelle année a été lancé l'intranet communautaire DUTLER ?",
            "reference": "2005.",
            "reference_pages": [6]
        },
        {
            "question": "Depuis quelle année Davidson est-elle certifiée B Corp ?",
            "reference": "2018.",
            "reference_pages": [6, 9]
        },
        {
            "question": "Quels sont les trois piliers d'impact sur lesquels s'appliquent les quatre axes de la stratégie Impact ?",
            "reference": "L'impact social, l'impact sociétal et l'impact environnemental.",
            "reference_pages": [7]
        },
        {
            "question": "Quels sont les quatre axes appliqués sans exception aux trois piliers d'impact ?",
            "reference": "Mesurer, réduire, augmenter et partager.",
            "reference_pages": [7]
        },
        {
            "question": "Quelles sont les certifications auditées de Davidson ?",
            "reference": "B Corp, ISO 9001:2015, ISO/IEC 27001:2022 et Qualiopi.",
            "reference_pages": [9]
        },
        {
            "question": "Quelle est la note EcoVadis 2025 de Davidson ?",
            "reference": "74/100, avec une médaille Silver.",
            "reference_pages": [9]
        },
        {
            "question": "Qui compose la Direction Impact rattachée à la Direction générale ?",
            "reference": "Maëliss Delacroix, Océane Serpin et Thomas Tailhandier.",
            "reference_pages": [10]
        },
        {
            "question": "Depuis quand chaque nouvelle mission est-elle évaluée au regard des 17 Objectifs de Développement Durable ?",
            "reference": "Depuis 2022.",
            "reference_pages": [13]
        },
        {
            "question": "Quel est le total de nouvelles missions ODD (C2 Nouveaux clients, M2, M3) en 2022 ?",
            "reference": "52 nouvelles missions ODD.",
            "reference_pages": [14]
        },
        {
            "question": "Quel est le stock actif de missions ODD (C2 Nouveaux clients, M2, M3) en 2022 ?",
            "reference": "60 missions ODD actives.",
            "reference_pages": [14]
        },
        {
            "question": "Quel est le CA annuel associé en k€ (C2 Nouveaux clients, M2, M3) en 2023 ?",
            "reference": "19 215 k€.",
            "reference_pages": [14]
        },
        {
            "question": "Quel CA les missions ODD représentent-elles en 2025 et quelle part du CA 2025 ?",
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
            "question": "Quelles sont les mesures de Davidson pour la mobilité domicile-travail ?",
            "reference": "Proposer le télétravail lorsque cela est possible, encourager les mobilités durables avec le Forfait Mobilité Durable ou une aide spécifique, et proposer par exemple le prêt temporaire d'un vélo.",
            "reference_pages": [17]
        },
        {
            "question": "Quel est l'engagement d'ancrage local de Davidson pour les clients situés à moins de 80 km de ses bureaux régionaux ?",
            "reference": "Plus de 80 % des missions, pour un objectif d'au moins 75 %.",
            "reference_pages": [18]
        },
        {
            "question": "Sur quels trois principes repose la satisfaction de nos clients ?",
            "reference": "L'excellence opérationnelle, la transparence relationnelle et l'amélioration continue.",
            "reference_pages": [19]
        },
        {
            "question": "Dans la répartition femmes / hommes 2025, combien de femmes et quelle part de l'effectif global ?",
            "reference": "693 femmes, soit 30 % de l'effectif global.",
            "reference_pages": [24]
        },
        {
            "question": "Quel est le taux d'emploi direct des personnes en situation de handicap en 2025 ?",
            "reference": "1,8 %.",
            "reference_pages": [25]
        },
        {
            "question": "Quels sont le Trust Index et la perception globale Great Place To Work 2024 ?",
            "reference": "Trust Index de 83/100 et perception globale de 87/100.",
            "reference_pages": [9, 29]
        },
        {
            "question": "SoliDav 2025 : combien de salarié(e)s engagé(e)s et combien d'heures données ?",
            "reference": "283 salariés engagés et 1 782 heures données.",
            "reference_pages": [34, 36, 75, 80]
        },
        {
            "question": "SoliDav, résultats et impact mesuré : combien de missions et d'associations en 2025 ?",
            "reference": "563 missions et 74 associations.",
            "reference_pages": [36, 75, 80]
        },
        {
            "question": "Quels sont les résultats globaux du bilan carbone 2025 en tCO2e, et ceux des Scopes 1 & 2 et du Scope 3 ?",
            "reference": "7 590 tCO2e, dont 560 tCO2e pour les scopes 1 et 2 et 7 030 tCO2e pour le scope 3.",
            "reference_pages": [44]
        },
        {
            "question": "Dans la trajectoire SBTi, quel est l'objectif pour les émissions Scopes 1 & 2 ?",
            "reference": "Une réduction absolue de 50,4 % des émissions des scopes 1 et 2 par rapport à 2022.",
            "reference_pages": [45]
        },
        {
            "question": "Dans la trajectoire SBTi, quel est l'objectif de consommation d'énergie ?",
            "reference": "Atteindre 100 % d'énergie renouvelable en 2030.",
            "reference_pages": [45]
        },
        {
            "question": "Comment devons-nous protéger la confidentialité des données dont nous disposons ?",
            "reference": "Chaque collaborateur doit protéger la confidentialité des informations appartenant à Davidson ou à des tiers, ne les transmettre que dans un cadre professionnel légitime et prévenir le délit d'initié ainsi que la divulgation d'informations privilégiées.",
            "reference_pages": [54]
        },
        {
            "question": "Quel montant est reversé annuellement à une association d'intérêt général œuvrant en faveur des Droits Humains ?",
            "reference": "10 000 euros par an.",
            "reference_pages": [55]
        },
        {
            "question": "Quels sont les axes 01, 02 et 03 des engagements Right Tech ?",
            "reference": "Mesurer et piloter les impacts numériques ; réduire les externalités négatives par l'écoconception et la sobriété ; augmenter les externalités positives grâce aux contributions collectives et aux outils numériques à impact.",
            "reference_pages": [58]
        },

        # --- Réponses lisibles seulement dans une image (graphique, logo) ---
        {
            "question": "Dans le graphique de la trajectoire SBTi, quelles sont les émissions Scopes 1 & 2 en 2023 ?",
            "reference": "936 tCO2e.",
            "reference_pages": [45]
        },
        {
            "question": "Dans le graphique de la trajectoire SBTi, quelles sont les émissions Scope 3 en 2024 ?",
            "reference": "6 476 tCO2e.",
            "reference_pages": [45]
        },

        # --- Réponse absente du document : le RAG doit le dire ---
        {
            # "Networks" n'apparaît que dans une infographie, sans chiffre
            "question": "Quelle part de l'activité de Davidson représente Networks ?",
            "reference": "Cette information n'est pas indiquée dans le document.",
            "reference_pages": [5]
        }
    ]


    return pd.DataFrame(data)


if __name__ == "__main__":

    from pathlib import Path

    df = build_dataset()

    output_path = Path(__file__).resolve().parent / "dataset_mots_pdf.csv"

    df.to_csv(
        output_path,
        index=False,
        encoding="utf-8-sig"
    )

    print(df.to_string(index=False))
    print(f"\nDataset sauvegardé : {output_path}")
