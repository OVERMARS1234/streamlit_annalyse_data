import pandas as pd
from sqlalchemy import create_engine

# Fonction pour établir une connexion à la base de données
def connect_to_db():
    try:
        engine = create_engine("postgresql://postgres:password@localhost:5432/postgres")
        return engine
    except Exception as e:
        print(f"Erreur de connexion à la base de données : {e}")
        return None

# Fonction pour récupérer les villes distinctes depuis la base de données
def get_villes_from_db():
    engine = connect_to_db()
    if engine is None:
        return []

    query = """
    SELECT DISTINCT v.name
    FROM villes v
    """

    try:
        villes = pd.read_sql(query, engine)
        return villes["name"].tolist()  # Liste des villes distinctes
    except Exception as e:
        print(f"Erreur lors de la récupération des villes : {e}")
        return []

# Fonction pour récupérer les données avec filtres et pagination
def get_filtered_data(price_range, rooms, bathrooms, city, date_range, page=1, per_page=20):
    engine = connect_to_db()
    if engine is None:
        return pd.DataFrame()

    query = """
    SELECT a.id, a.price, a.surface_area, a.nb_rooms, a.nb_baths, v.name AS city, a.datetime
    FROM annonces a
    JOIN villes v ON a.city_id = v.id
    WHERE CAST(a.price AS numeric) BETWEEN %(min_price)s AND %(max_price)s
      AND a.nb_rooms BETWEEN %(min_rooms)s AND %(max_rooms)s
      AND a.nb_baths BETWEEN %(min_bathrooms)s AND %(max_bathrooms)s
      AND v.name = %(city)s
    """

    if date_range:
        query += " AND a.datetime BETWEEN %(start_date)s AND %(end_date)s"
    
    query += " LIMIT %(per_page)s OFFSET %(offset)s"

    params = {
        "min_price": price_range[0],
        "max_price": price_range[1],
        "min_rooms": rooms[0],
        "max_rooms": rooms[1],
        "min_bathrooms": bathrooms[0],
        "max_bathrooms": bathrooms[1],
        "city": city,
        "per_page": per_page,
        "offset": (page - 1) * per_page
    }

    if date_range:
        params["start_date"] = date_range[0]
        params["end_date"] = date_range[1]

    try:
        data = pd.read_sql(query, engine, params=params)
        return data
    except Exception as e:
        print(f"Erreur lors de l'exécution de la requête : {e}")
        return pd.DataFrame()

# Fonction pour récupérer les valeurs min et max des champs prix, chambres, salles de bain
def get_min_max_values():
    engine = connect_to_db()
    if engine is None:
        return {"price_min": 0, "price_max": 1000000, "rooms_min": 1, "rooms_max": 10, "baths_min": 1, "baths_max": 5}

    query = """
    SELECT 
        MIN(price) AS price_min, MAX(price) AS price_max,
        MIN(nb_rooms) AS rooms_min, MAX(nb_rooms) AS rooms_max,
        MIN(nb_baths) AS baths_min, MAX(nb_baths) AS baths_max
    FROM annonces
    """

    try:
        min_max_values = pd.read_sql(query, engine)
        values = min_max_values.iloc[0]  # Extraire les valeurs uniques

        # Conversion explicite en type numérique pour éviter les erreurs de type
        return {
            "price_min": float(values["price_min"]),
            "price_max": float(values["price_max"]),
            "rooms_min": int(values["rooms_min"]),
            "rooms_max": int(values["rooms_max"]),
            "baths_min": int(values["baths_min"]),
            "baths_max": int(values["baths_max"])
        }
    except Exception as e:
        print(f"Erreur lors de la récupération des min/max : {e}")
        return {"price_min": 0, "price_max": 1000000, "rooms_min": 1, "rooms_max": 10, "baths_min": 1, "baths_max": 5}
