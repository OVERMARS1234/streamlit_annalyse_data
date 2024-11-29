from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime
import pandas as pd

# Connexion à la base de données
def connect_to_db():
    try:
        engine = create_engine("postgresql://postgres:password@localhost:5432/postgres")
        return engine
    except Exception as e:
        print(f"Erreur de connexion à la base de données : {e}")
        return None

# Fonction pour récupérer ou créer une ville
def get_or_create_ville(name, session):
    ville = session.query(Ville).filter_by(name=name).first()
    if ville is None:
        ville = Ville(name=name)
        session.add(ville)
        session.commit()
    return ville

# Fonction pour récupérer ou créer un équipement
def get_or_create_equipement(name, session):
    equipement = session.query(Equipement).filter_by(name=name).first()
    if equipement is None:
        equipement = Equipement(name=name)
        session.add(equipement)
        session.commit()
    return equipement

# Insertion des données dans la base de données
def insert_data(df):
    engine = connect_to_db()
    if engine is None:
        return
    
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        for _, row in df.iterrows():
            ville = get_or_create_ville(row['Localisation'], session)
            
            annonce = Annonce(
                title=row['Title'],
                price=row['Price'] if pd.notnull(row['Price']) else "PRIX NON SPÉCIFIÉ",
                datetime=datetime.strptime(row['Date'], '%Y-%m-%d'),
                nb_rooms=row['Chambre'] if pd.notnull(row['Chambre']) else None,
                nb_baths=row['Salle de bain'] if pd.notnull(row['Salle de bain']) else None,
                surface_area=row['Surface habitable'] if pd.notnull(row['Surface habitable']) else None,
                link=row['EquipementURL'],
                ville=ville
            )
            session.add(annonce)

            for equip_col in equipement_columns:
                if row[equip_col] == True:
                    equipement = get_or_create_equipement(equip_col, session)
                    annonce_equipement = AnnonceEquipement(annonce_id=annonce.id, equipement_id=equipement.id)
                    session.add(annonce_equipement)
        
        session.commit()
        
    except SQLAlchemyError as e:
        session.rollback()
        print(f"Erreur lors de l'insertion des données : {e}")
    finally:
        session.close()
