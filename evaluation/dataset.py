import pandas as pd

def build_dataset():
    
    data = [
        {
            "question": "Quelle est l'activité principale de Davidson Consulting ?",
            "reference": "Davidson Consulting est un acteur du conseil en management et en expertises technologiques.",
            "reference_pages": [5]
        },
        {
            "question": "Quelle proportion des compétences des consultants Davidson est liée au secteur numérique ?",
            "reference": "70 % des compétences des consultants sont liées au secteur numérique.",
            "reference_pages": [5]
        },
        {
            "question": "En quelle année l'intranet communautaire DUTLER a-t-il été créé ?",
            "reference": "2005.",
            "reference_pages": [6]
        },
        {
            "question": "En quelle année Davidson a-t-elle obtenu sa première certification B Corp ?",
            "reference": "2018.",
            "reference_pages": [6]
        },
        {
            "question": "Quels sont les trois piliers de la stratégie Impact de Davidson ?",
            "reference": "L'impact social, l'impact sociétal et l'impact environnemental.",
            "reference_pages": [7]
        },
        {
            "question": "Quels sont les quatre axes appliqués aux piliers de la stratégie Impact ?",
            "reference": "Mesurer, réduire, augmenter et partager.",
            "reference_pages": [7]
        },
        {
            "question": "Quelles sont les quatre certifications auditées présentées par Davidson ?",
            "reference": "B Corp, ISO 9001:2015, ISO/IEC 27001:2022 et Qualiopi.",
            "reference_pages": [9]
        },
        {
            "question": "Quelle note Davidson a-t-elle obtenue à l'évaluation EcoVadis 2025 ?",
            "reference": "74/100, avec une médaille Silver.",
            "reference_pages": [9]
        },
        {
            "question": "Qui compose l'équipe Impact rattachée à la Direction générale ?",
            "reference": "Maëliss Delacroix, Océane Serpin et Thomas Tailhandier.",
            "reference_pages": [10]
        },
        {
            "question": "Depuis quelle année Davidson évalue-t-elle chaque nouvelle mission selon les Objectifs de Développement Durable ?",
            "reference": "Depuis 2022.",
            "reference_pages": [13]
        },
        {
            "question": "Combien de nouvelles missions ODD de niveaux C2, M2 et M3 ont été enregistrées en 2022 ?",
            "reference": "52 nouvelles missions ODD.",
            "reference_pages": [14]
        },
        {       
            "question": "Quel était le stock actif de missions ODD en 2022 ?",
            "reference": "60 missions ODD actives.",
            "reference_pages": [14]
        },
        {
            "question": "Quel était le chiffre d'affaires annuel associé aux missions ODD en 2023, en k€ ?",
            "reference": "19 215 k€.",
            "reference_pages": [14]
        },
        {
            "question": "Quel chiffre d'affaires les missions ODD ont-elles représenté en 2025 ?",
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
            "question": "Quelles mesures Davidson propose-t-elle pour réduire l'impact des déplacements domicile-travail ?",
            "reference": "Proposer le télétravail lorsque cela est possible, encourager les mobilités durables avec le Forfait Mobilité Durable ou une aide spécifique, et proposer par exemple le prêt temporaire d'un vélo.",
            "reference_pages": [17]
        },
        {
            "question": "Quelle part des missions de Davidson est réalisée pour des clients situés à moins de 80 km de ses bureaux régionaux ?",
            "reference": "Plus de 80 % des missions, pour un objectif d'au moins 75 %.",
            "reference_pages": [18]
        },
        {
            "question": "Quels sont les trois principes de la politique de satisfaction client de Davidson ?",
            "reference": "L'excellence opérationnelle, la transparence relationnelle et l'amélioration continue.",
            "reference_pages": [19]
        },
        {
            "question": "Combien de femmes travaillaient chez Davidson en 2025 et quelle proportion de l'effectif représentaient-elles ?",
            "reference": "693 femmes, soit 30 % de l'effectif global.",
            "reference_pages": [24]
        },
        {
            "question": "Quel était le taux d'emploi direct des personnes en situation de handicap chez Davidson en 2025 ?",
            "reference": "1,8 %.",
            "reference_pages": [25]
        },
        {
            "question": "Quels étaient les résultats du Trust Index et de la perception globale Great Place To Work en 2024 ?",
            "reference": "Trust Index de 83/100 et perception globale de 87/100.",
            "reference_pages": [9, 29]
        },
        {
            "question": "Combien de salariés se sont engagés dans SoliDav en 2025 et combien d'heures ont été données ?",
            "reference": "283 salariés engagés et 1 782 heures données.",
            "reference_pages": [34, 36, 75, 80]
        },
        {
            # Page 36 : les chiffres sont écrits sans leur libellé ;
            # la phrase complète est aux pages 75 et 80
            "question": "Combien de missions et d'associations ont été concernées par SoliDav en 2025 ?",
            "reference": "563 missions et 74 associations.",
            "reference_pages": [36, 75, 80]
        },
        {
            "question": "Quel était le bilan carbone global de Davidson en 2025 dans le périmètre validé par SBTi ?",
            "reference": "7 590 tCO2e, dont 560 tCO2e pour les scopes 1 et 2 et 7 030 tCO2e pour le scope 3.",
            "reference_pages": [44]
        },
        {
            "question": "Quel objectif de réduction des émissions des scopes 1 et 2 Davidson vise-t-elle en 2032 par rapport à 2022 ?",
            "reference": "Une réduction absolue de 50,4 % des émissions des scopes 1 et 2 par rapport à 2022.",
            "reference_pages": [45]
        },
        {
            "question": "Quel est l'objectif de Davidson concernant l'utilisation d'énergie renouvelable en 2030 ?",
            "reference": "Atteindre 100 % d'énergie renouvelable en 2030.",
            "reference_pages": [45]
        },
        {
            "question": "Quelle est la politique de Davidson concernant la confidentialité des données et la sécurité de l'information ?",
            "reference": "Chaque collaborateur doit protéger la confidentialité des informations appartenant à Davidson ou à des tiers, ne les transmettre que dans un cadre professionnel légitime et prévenir le délit d'initié ainsi que la divulgation d'informations privilégiées.",
            "reference_pages": [54]
        },
        {
            "question": "Quel montant annuel Davidson prévoit-elle pour soutenir une association de défense des droits humains ?",
            "reference": "10 000 euros par an.",
            "reference_pages": [55]
        },
        {
            "question": "Quels sont les trois premiers axes des engagements Right Tech de Davidson ?",
            "reference": "Mesurer et piloter les impacts numériques ; réduire les externalités négatives par l'écoconception et la sobriété ; augmenter les externalités positives grâce aux contributions collectives et aux outils numériques à impact.",
            "reference_pages": [58]
        },

        # --- Réponses lisibles seulement dans une image (graphique, logo) ---
        {
            "question": "Quelles étaient les émissions des scopes 1 et 2 de Davidson en 2023 ?",
            "reference": "936 tCO2e.",
            "reference_pages": [45]
        },
        {
            "question": "Quelles étaient les émissions du scope 3 de Davidson en 2024 ?",
            "reference": "6 476 tCO2e.",
            "reference_pages": [45]
        },

        # --- Mêmes informations, demandées avec les mots du PDF ---
        # À comparer avec les questions ci-dessus : si celles-ci réussissent
        # et les autres échouent, c'est la recherche Qdrant qui est en cause
        {
            "question": "Quels sont les trois piliers d'impact sur lesquels s'appliquent les quatre axes de la stratégie Impact ?",
            "reference": "L'impact social, l'impact sociétal et l'impact environnemental.",
            "reference_pages": [7]
        },
        {
            "question": "Quel est le nombre global de femmes et d'hommes chez Davidson en 2025 ?",
            "reference": "693 femmes et 1 633 hommes, soit 2 326 salariés au total.",
            "reference_pages": [24]
        },
        {
            "question": "Dans la trajectoire SBTi, quel est l'objectif de consommation d'énergie ?",
            "reference": "100 % d'énergie renouvelable en 2030, comparé à 2022 (89 % initialement).",
            "reference_pages": [45]
        },
        {
            "question": "Dans la trajectoire SBTi, quel est l'objectif pour les émissions Scope 3 ?",
            "reference": "-58,2 % en 2032, en relatif par rapport à la valeur ajoutée (tCO2e/M€VA), comparé à 2022.",
            "reference_pages": [45]
        },
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
            "question": "Quelle part de l'activité de Davidson représente l'offre Networks ?",
            "reference": "Cette information n'est pas indiquée dans le document.",
            "reference_pages": [5]
        }
    ]


    return pd.DataFrame(data)


if __name__ == "__main__":

    from pathlib import Path

    df = build_dataset()

    output_path = Path(__file__).resolve().parent / "dataset.csv"

    df.to_csv(
        output_path,
        index=False,
        encoding="utf-8-sig"
    )

    print(df.to_string(index=False))
    print(f"\nDataset sauvegardé : {output_path}")