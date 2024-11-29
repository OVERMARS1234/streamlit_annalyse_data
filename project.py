import pandas as pd
import plotly.express as px
import streamlit as st
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Configuration du tableau de bord
st.set_page_config(
    page_title="Tableau de Bord Immobilier",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Fonction pour établir une connexion à la base de données
@st.cache_resource
def connect_to_db():
    try:
        engine = create_engine("postgresql://postgres:password@localhost:5432/postgres")
        return engine
    except Exception as e:
        st.error(f"Erreur de connexion à la base de données : {e}")
        return None

# Fonction pour récupérer toutes les données
@st.cache_data
def get_all_data():
    engine = connect_to_db()
    if engine is None:
        return pd.DataFrame()

    query = """
    SELECT a.id, a.price, a.surface_area, a.nb_rooms, a.nb_baths, v.name AS city, a.datetime, 
           v.latitude, v.longitude, array_agg(e.name) AS equipments
    FROM annonces a
    JOIN villes v ON a.city_id = v.id
    LEFT JOIN annonce_equipement ae ON a.id = ae.annonce_id
    LEFT JOIN equipements e ON ae.equipement_id = e.id
    GROUP BY a.id, v.name, v.latitude, v.longitude
    """
    try:
        data = pd.read_sql(query, engine)
        return data
    except Exception as e:
        st.error(f"Erreur lors de l'exécution de la requête : {e}")
        return pd.DataFrame()

# Fonction pour nettoyer les données
def clean_data(data):
    data['price'] = pd.to_numeric(data['price'], errors='coerce')
    data['surface_area'] = pd.to_numeric(data['surface_area'], errors='coerce')
    data['datetime'] = pd.to_datetime(data['datetime'], errors='coerce')
    data['latitude'] = pd.to_numeric(data['latitude'], errors='coerce')
    data['longitude'] = pd.to_numeric(data['longitude'], errors='coerce')
    data.dropna(subset=['price', 'datetime', 'latitude', 'longitude'], inplace=True)
    return data

# Fonction principale pour afficher le tableau de bord
def show_dashboard():
    st.title("🏡 Tableau de Bord Immobilier")
    st.markdown("Bienvenue dans tableau de bord interactif pour explorer et analyser les données immobilières.")

    # Récupération des données
    data = get_all_data()
    if data.empty:
        st.error("Aucune donnée disponible.")
        return

    data = clean_data(data)

    # **Filtres**
    st.sidebar.header("🎛️ Filtres")
    cities = data['city'].unique()
    selected_city = st.sidebar.selectbox("🌍 Ville", ["Toutes"] + list(cities))
    price_min, price_max = st.sidebar.slider("💰 Gamme de prix (DH)", int(data['price'].min()), int(data['price'].max()), (100000, 500000), step=5000)
    nb_rooms = st.sidebar.slider("🛏️ Nombre de pièces", 0, 10, (1, 5))
    nb_baths = st.sidebar.slider("🚿 Nombre de salles de bain", 0, 5, (1, 3))
    equipements = st.sidebar.multiselect(
        "🔧 Équipements disponibles",
        ['Climatisation', 'Balcon', 'Parking', 'Ascenseur', 'Chauffage', 'Concierge', 'Terrasse', 'Duplex']
    )

    # Application des filtres
    filtered_data = data[
        (data['price'].between(price_min, price_max)) &
        (data['nb_rooms'].between(*nb_rooms)) &
        (data['nb_baths'].between(*nb_baths))
    ]
    if selected_city != "Toutes":
        filtered_data = filtered_data[filtered_data['city'] == selected_city]
    if equipements:
        filtered_data = filtered_data[filtered_data['equipments'].apply(lambda x: any(e in x for e in equipements))]

    # **Indicateurs Clés**
    st.subheader("📊 Indicateurs Clés")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("📋 Nombre total d'annonces", len(filtered_data))
    with col2:
        st.metric("💶 Prix moyen (DH)", f"{filtered_data['price'].mean():,.2f}" if not filtered_data.empty else "N/A")
    with col3:
        st.metric("📐 Surface moyenne (m²)", f"{filtered_data['surface_area'].mean():,.2f}" if not filtered_data.empty else "N/A")

    st.markdown("---")

    # **Carte Interactive**
    st.subheader("🌍 Répartition des annonces sur la carte")
    if not filtered_data.empty:
        fig_map = px.scatter_mapbox(
            filtered_data,
            lat="latitude",
            lon="longitude",
            hover_name="city",
            hover_data=["price", "surface_area", "nb_rooms", "nb_baths"],
            color="price",
            size="surface_area",
            size_max=10,
            color_continuous_scale="Viridis",
            title="Répartition des annonces immobilières",
        )
        fig_map.update_layout(mapbox_style="carto-positron", mapbox_zoom=5, mapbox_center={
            "lat": filtered_data['latitude'].mean(),
            "lon": filtered_data['longitude'].mean()
        })
        st.plotly_chart(fig_map)

    # **Répartition des annonces par ville**
    st.subheader("📍 Nombre d'annonces par ville ")
    if not filtered_data.empty:
        city_counts = filtered_data['city'].value_counts().reset_index()
        city_counts.columns = ['city', 'number_of_ads']
        city_counts = city_counts.sort_values(by="number_of_ads", ascending=False)
        fig_bar = px.bar(
            city_counts,
            x='city',
            y='number_of_ads',
            title="Nombre d'annonces par ville (avec annotations)",
            labels={"city": "Ville", "number_of_ads": "Nombre d'annonces"},
            text='number_of_ads',
            color='number_of_ads',
            color_continuous_scale="Plasma"
        )
        fig_bar.update_traces(
            texttemplate='%{text}',
            textposition='outside'
        )
        fig_bar.update_layout(
            uniformtext_minsize=8,
            uniformtext_mode='hide',
            xaxis=dict(title="Ville", tickangle=-45),
            yaxis=dict(title="Nombre d'annonces"),
            coloraxis_showscale=False
        )
        st.plotly_chart(fig_bar, use_container_width=True)

    # **Analyse des Prix par Ville**
    st.subheader("💰 Prix moyen par ville")
    if not filtered_data.empty:
        avg_price_by_city = filtered_data.groupby('city')['price'].mean().reset_index()
        avg_price_by_city = avg_price_by_city.sort_values(by="price", ascending=False)
        fig_avg_price = px.bar(
            avg_price_by_city,
            x="city",
            y="price",
            title="Prix moyen des annonces par ville",
            text='price',
            labels={"city": "Ville", "price": "Prix moyen (DH)"},
            color='price',
            color_continuous_scale="Blues"
        )
        fig_avg_price.update_layout(
            xaxis=dict(title="Ville", tickangle=-45),
            yaxis=dict(title="Prix moyen (DH)")
        )
        st.plotly_chart(fig_avg_price)

    # **Analyse des Prix**
    st.subheader("💰 Analyse des Prix")
    fig_hist = px.histogram(
        filtered_data,
        x="price",
        nbins=30,
        title="Répartition des prix",
        labels={"price": "Prix (DH)"},
        color_discrete_sequence=["#636EFA"]
    )
    st.plotly_chart(fig_hist)

    # **Boxplot des prix par ville**
    st.subheader("📊 Boxplot des prix par ville")
    fig_box = px.box(
        filtered_data,
        x="city",
        y="price",
        title="Boxplot des prix par ville",
        labels={"city": "Ville", "price": "Prix (DH)"}
    )
    st.plotly_chart(fig_box)

    # **Répartition des équipements**
    st.subheader("🔧 Répartition des équipements")
    if not filtered_data.empty:
        equip_counts = filtered_data['equipments'].explode().value_counts().reset_index()
        equip_counts.columns = ['equipment', 'count']
        fig_pie = px.pie(
            equip_counts,
            names='equipment',
            values='count',
            title="Répartition des équipements",
            color='count',
            color_discrete_sequence=px.colors.sequential.Plasma
        )
        st.plotly_chart(fig_pie)

    # **Graphique du nombre moyen de pièces et de salles de bain par ville**
    st.subheader("📏 Nombre moyen de pièces et de salles de bain par ville")
    if not filtered_data.empty:
        avg_rooms_baths = filtered_data.groupby('city').agg({'nb_rooms': 'mean', 'nb_baths': 'mean'}).reset_index()
        fig_bar_rooms_baths = px.bar(
            avg_rooms_baths,
            x='city',
            y=['nb_rooms', 'nb_baths'],
            title="Nombre moyen de pièces et de salles de bain par ville",
            labels={"value": "Nombre moyen", "city": "Ville"},
            barmode='group'
        )
        st.plotly_chart(fig_bar_rooms_baths)


    # **Relation entre surface et prix**
    st.subheader("📏 Relation entre Surface et Prix")
    if not filtered_data.empty:
        fig_scatter = px.scatter(
            filtered_data,
            x="surface_area",
            y="price",
            title="Relation entre Surface et Prix",
            labels={"surface_area": "Surface (m²)", "price": "Prix (DH)"},
            color="price",
            color_continuous_scale="Viridis"
        )
        st.plotly_chart(fig_scatter)


    # **Analyse temporelle : Évolution des annonces publiées au fil du temps**
    st.subheader("📅 Évolution du nombre d'annonces publiées")
    if not filtered_data.empty:
        filtered_data['month'] = filtered_data['datetime'].dt.to_period('M').astype(str)  # Convert to string format
        trend_data = filtered_data.groupby('month').size().reset_index(name='count')
        fig_trend = px.line(
            trend_data,
            x='month',
            y='count',
            title="Évolution du nombre d'annonces publiées au fil du temps",
            labels={"count": "Nombre d'annonces", "month": "Date"}
        )
        st.plotly_chart(fig_trend)

    # **Téléchargement des données filtrées**
    st.markdown("---")
    st.download_button(
        label="📥 Télécharger les données filtrées",
        data=filtered_data.to_csv(index=False),
        file_name="donnees_filtrees.csv",
        mime="text/csv"
    )

# Exécution
if __name__ == "__main__":
    show_dashboard()
