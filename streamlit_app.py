import streamlit as st
import networkx as nx
from pyvis.network import Network
import streamlit.components.v1 as components
import osmnx as ox
from shapely.geometry import LineString, Polygon, MultiLineString, MultiPolygon, Point
import json
from shapely.geometry import Point
from shapely.errors import TopologicalError
import pandas as pd
import plotly.express as px
import base64

def card(title, value, text=""):
    return f"""
    <div style='padding: 15px; background-color: #1e1e1e; border-radius: 10px;
                border: 1px solid #444; margin-bottom: 20px'>
        <h5 style='color: #ffd700; margin-top: 0'>{title}</h5>
        <div style='font-size: 24px; color: white; font-weight: bold'>{value}</div>
        <div style='color: #aaa; font-size: 14px; margin-top: 5px'>{text}</div>
    </div>
    """

def is_serializable(value):
    tipos_invalidos = (LineString, Polygon, MultiLineString, MultiPolygon, Point)
    if isinstance(value, tipos_invalidos):
        return False
    if isinstance(value, (list, dict)):
        try:
            json.dumps(value)
            return True
        except:
            return False
    return True

def draw_graph_pyvis(G):
    G_copy = nx.MultiDiGraph()

    for n, data in G.nodes(data=True):
        new_data = {k: v for k, v in data.items() if is_serializable(v)}
        acc = data.get("accident_count", 0)
        try:
            acc = int(float(acc)) if acc is not None else 0
        except:
            acc = 0
        grau = G.degree[n]
        rua = data.get("street_name", "Rua desconhecida")
        new_data["title"] = f"Nó: {n}<br>Rua: {rua}<br>Acidentes: {acc}<br>Grau: {grau}"
        new_data["label"] = str(acc) if acc > 0 else ""
        G_copy.add_node(n, **new_data)

    for u, v, k, data in G.edges(keys=True, data=True):
        new_data = {k: v for k, v in data.items() if is_serializable(v)}
        G_copy.add_edge(u, v, key=k, **new_data)

    net = Network(height="600px", width="100%", bgcolor="#ffffff", font_color="black")
    net.from_nx(G_copy)

    net.set_options("""
    var options = {
      "nodes": {
        "shape": "dot",
        "scaling": {
          "min": 5,
          "max": 20
        }
      },
      "edges": {
        "color": {"inherit": true},
        "smooth": false
      },
      "physics": {
        "barnesHut": {
          "gravitationalConstant": -30000,
          "centralGravity": 0.3,
          "springLength": 95
        },
        "minVelocity": 0.75
      }
    }
    """)

    net.save_graph("graph.html")
    with open("graph.html", "r", encoding="utf-8") as f:
        html = f.read()
    components.html(html, height=600, scrolling=False)

@st.cache_data
def load_grafo_graphml(path):
    G = ox.load_graphml(path)
    return G

st.set_page_config(layout="wide", page_title="Análise de Acidentes")
                #,initial_sidebar_state="expanded")
st.markdown("<script>window.scrollTo(0, 0);</script>", unsafe_allow_html=True)

graph_path = "results_brooklyn_2025/brooklyn_graph_with_accidents.graphml"

# grafo total (mt pesado)----------------------------------------------------
G = load_grafo_graphml(graph_path) 

#grafo só acidentes
nodes_com_acidente = [n for n, data in G.nodes(data=True) if data.get("accident_count", 0) and int(float(data.get("accident_count", 0))) > 0]
G_acidentes = G.subgraph(nodes_com_acidente).copy() 

#grafo só brooklyn-----------------------------------------------------------
gdf_brooklyn = ox.geocode_to_gdf("Brooklyn, New York, USA")
gdf_brooklyn = gdf_brooklyn.to_crs(epsg=4326)
polygon = gdf_brooklyn.geometry.iloc[0]

polygon = gdf_brooklyn.to_crs(epsg=4326).geometry.iloc[0]

nodes_brooklyn = []
for n, data in G.nodes(data=True):
    lat = data.get("y")
    lon = data.get("x")
    if lat is not None and lon is not None:
        try:
            ponto = Point(lon, lat)
            if polygon.contains(ponto):
                nodes_brooklyn.append(n)
        except TopologicalError:
            continue

G_brooklyn = G.subgraph(nodes_brooklyn).copy() 

#grafo só acidentes de brooklyn----------------------------------------------
nodes_com_acidente_brooklyn = [n for n, data in G_brooklyn.nodes(data=True) if data.get("accident_count", 0) and int(float(data.get("accident_count", 0))) > 0]
G_acidentes_brooklyn = G.subgraph(nodes_com_acidente_brooklyn).copy() 

# streamlit
img_path = "results_brooklyn_2025/images/"
width = 1000

st.sidebar.title("Navegação")

page = st.sidebar.selectbox(
    "Escolha uma página",
    ["Visão Geral",
    "Matriz de Adjacência e Densidade",
    "Diâmetro e Nós Adjacentes",
    "Histogramas",
    "Coeficiente de Clustering",
    "Componentes Conectados",
    "Medidas de Centralidade"]
)

st.sidebar.markdown("""
                    ### Links úteis
                    [Visualização do Gephi](https://gusless.github.io/brooklyn-map-gephi-network/)

                    [Colab](https://colab.research.google.com/drive/1qeaTKpWjrGRLzF8JMKPvBr9VTRjGxOkB#scrollTo=epExIrHVxVwI)

                    [GitHub](https://github.com/gusless/network-analysis-broklyn-traffic-accidents)
                    """)



if page == "Visão Geral":
    st.title("Análise de Redes - Acidentes em Brooklyn e Staten Island")

    st.markdown("Essa projeto se trata de uma análise da rede viária de Brooklyn e Staten Island, dois bairros de New York City, com foco em acidentes registrados entre os dias 01-Jan-2025 e 06-Jul-2025.")

    st.header("Mapa de Acidentes")

    st.markdown("""
                O grafo utilizado nesse projeto é representado pelo mapa a seguir, na qual representa os dois bairros em questão, sendo os *nós* representando pontos de interesse na rede viária, podendo ser as interseções entre os trechos (esquinas, cruzamentos, _interchanges_) e pontos finais das ruas. Já as **arestas** representam os segmentos das ruas que vão de um nó a outro, possuem valores como o nome da rua, comprimento, etc.
                """)

    st.image(img_path + "brooklyn_statenisld_accidents_map.png", width=width)

    n_nodes = len(G.nodes())
    n_edges = len(G.edges())
    col1, col2, col3 = st.columns(3)
    col1.markdown(card("Total de Nós", f"{n_nodes:,}".replace(",",".")), unsafe_allow_html=True)
    col2.markdown(card("Total de Arestas", f"{n_edges:,}".replace(",",".")), unsafe_allow_html=True)
    col3.markdown(card(
        "Total de Acidentes",
        f"""{sum(
            int(float(G.nodes[node].get("accident_count", 0) or 0))
            for node in G.nodes
        )-284:,}""".replace(",", ".") #<- nó equivocado
    ), unsafe_allow_html=True)

    with st.expander("Fonte dos acidentes"):
            st.markdown("""
            [NYC OpenData](https://data.cityofnewyork.us/Public-Safety/Motor-Vehicle-Collisions-Crashes/h9gi-nx95/about_data)
            """)

elif page == "Matriz de Adjacência e Densidade":
    # matriz ---------------------------
    st.header("Matriz de Adjacência (100x100)")

    st.markdown("A matriz ficou com uma quantidade muito alta de 0, isso indica que o grafo é esparso, com os nós possuíndo poucas conexões entre si. Algo típico de uma rede viária")

    G_simple = nx.Graph(G)

    adj_matrix = nx.adjacency_matrix(G_simple)
    small_adj = adj_matrix[:100, :100].todense() 
    adj_df_small = pd.DataFrame(small_adj)
    st.dataframe(small_adj, height=300)

    # expersidade e densidade --------------
    density = round(nx.density(G), 6)

    st.subheader("Exparsidade e Densidade")

    st.markdown("Grafos urbanos tendem a ser muito esparso, já que seria impossível que todas as ruas se conectem entre si.")

    col1, col2 = st.columns(2)
    col1.markdown(card("Densidade", (density), "Proporção de conexões existentes no grafo"), unsafe_allow_html=True)
    col2.markdown(card("Esparsidade", 1 - density, "Proporção de conexões ausentes no grafo"), unsafe_allow_html=True)

elif page == "Diâmetro e Nós Adjacentes":
    # diametro ----------------------------
    st.header("Análise de Diâmetro e nós adjacentes")

    st.markdown("O diâmetro é a menor distancia possível (em número de nós, não confundir com quilometragem) de um nó até outro, nesse caso séria a menor distância de um ponto a outro do mapa.")

    def show_diameter_and_km(nodes, km):
        col1, col2 = st.columns(2)
        col1.markdown(card("Valor do Diâmetro", f"{nodes} nós", "Maior distância entre dois nós"), unsafe_allow_html=True)
        col2.markdown(card("Quilometragem", f"{km} Km", "Maior distância entre dois nós"), unsafe_allow_html=True)

    tipo = st.selectbox(
        "Rotas de diâmetro",
        [
            "Menor distância entre nós periféricos",
            "Menor distância entre nós periféricos em quilômetros",
            "Menor distância entre pontos extremos do mapa"
        ]
    )

    if tipo == "Menor distância entre nós periféricos":
        st.subheader("Menor distância entre nós periféricos")
        show_diameter_and_km(142, 63.36)
        st.markdown("Maior diâmetro do mapa, representando o menor caminho possível, percorrendo nós, de um nó periférico e outro")
        st.image(img_path + "brooklyn_statenisld_accidents_diameter_map.png", width=width)

    elif tipo == "Menor distância entre nós periféricos em quilômetros":
        st.subheader("Menor distância entre nós periféricos em quilômetros")
        show_diameter_and_km(286, 30.7)
        st.markdown("Menor distância em quilômetros entre os dois nós periféricos, não representa o maior caminho possível em distância real")
        st.image(img_path + "brooklyn_statenisld_accidents_diameter_real_distance_map.png", width=width)

    elif tipo == "Menor distância entre pontos extremos do mapa":
        st.subheader("Menor distância entre pontos extremos do mapa")
        show_diameter_and_km(439, 41.75)
        st.markdown("""
                    Menor distância possível de dois pontos mais extremos, escolhidos manualmente. O critério utilizado, foi coletar o ponto mais ao leste e o mais ao norte do mapa, já que a geografia da região favorece essa escolha. 
                    > Esses pontos podem não ser os pontos mais distantes entre si, visto que não foi utilizado nenhum algoritmo para identificá-los.
                    """)
        st.image(img_path + "brooklyn_statenisld_accidents_distance_real_2_distants_nodes_map.png", width=width)

elif page == "Histogramas":
    # histograma ---------------------------

    st.subheader("Histogramas de Distribuição de Grau")

    st.markdown("""
                Na distribuição exatas de graus foi notado uma quantidade significativa de nós apresentando grau 4 e 6, havendo pelo menos 8 mil com 6 graus, esses nós com alto grau podem ser grandes cruzamentos de grandes avenidas, enquanto os nós de grau 3 podem representar esquinas.
                Já os In-Degree e Out-Degree ficaram com uma quantidade muito parecida, essa distribuição representa os nós que iniciam ou terminam uma contra mão, indicando que os nós de grau 9 e 10 são as mão e contra-mão das vias somadas.
                """)

    graus_in = [G.in_degree(n) for n in G.nodes()]
    graus_out = [G.out_degree(n) for n in G.nodes()]
    degrees = [degree for _, degree in G.degree()]

    df_in = pd.DataFrame(graus_in, columns=['grau'])
    df_out = pd.DataFrame(graus_out, columns=['grau'])
    df_dg = pd.DataFrame(degrees, columns=['grau'])

    st.markdown("#### Degree total")
    fig_dg = px.histogram(
        df_dg, x='grau', nbins=20, title="Distribuição de grau",
        labels={"grau": "Grau"},
        color_discrete_sequence=["#ff6f61"],
        text_auto=True
    )
    fig_dg.update_traces(textfont_size=18)
    st.plotly_chart(fig_dg, use_container_width=True)

    # indegree
    st.markdown("#### In-degree")
    fig_in = px.histogram(
        df_in, x='grau', nbins=20, title="Distribuição de In-degree",
        labels={"grau": "Grau"},
        color_discrete_sequence=["#56cc9d"],
        text_auto=True
    )
    fig_in.update_traces(textfont_size=18)
    st.plotly_chart(fig_in, use_container_width=True)

    # outdegree
    st.markdown("#### Out-degree")
    fig_out = px.histogram(
        df_out, x='grau', nbins=20, title="Distribuição de Out-degree",
        labels={"grau": "Grau"},
        color_discrete_sequence=["#ff6f61"],
        text_auto=True
    )
    fig_out.update_traces(textfont_size=18)
    st.plotly_chart(fig_out, use_container_width=True)

elif page == "Coeficiente de Clustering":
    # clustering ---------------------------
    st.subheader("Coeficiente de Clustering")

    G_sub = nx.Graph(G)

    node_most_accidents = max(G_sub.nodes, key=lambda n: G_sub.nodes[n].get('accident_count', 0))

    def node_mais_acidentes_por_grau(G, grau):
        """Retorna o nó com maior número de acidentes entre os de grau especificado."""
        nodes_grau = [n for n, d in G.degree() if d == grau]
        if not nodes_grau:
            return None
        return max(nodes_grau, key=lambda n: G.nodes[n].get('accident_count', 0))

    node_degree_2 = node_mais_acidentes_por_grau(G_sub, 2)
    node_degree_3 = node_mais_acidentes_por_grau(G_sub, 3)
    node_degree_4 = node_mais_acidentes_por_grau(G_sub, 4)
    node_degree_5 = node_mais_acidentes_por_grau(G_sub, 5)
    node_degree_6 = node_mais_acidentes_por_grau(G_sub, 6)

    selected_nodes = [
        ("Grau 2", node_degree_2),
        ("Grau 3", node_degree_3),
        ("Grau 4", node_degree_4),
        ("Grau 5", node_degree_5),
        ("Grau 6", node_degree_6),
        ("Mais acidentes", node_most_accidents)
    ]

    st.markdown("O coeficiente de clustering foi bem baixo globalmente e para todos os nós escolhidos, além de ter sido 0 para alguns, isto é, não há nenhum triangulo formado entre as ruas que ele conecta.")

    st.markdown("#### Coeficiente de Clustering do nó com maior taxa de acidente por grau")

    global_clust = nx.average_clustering(G_sub)

    col1, col2 = st.columns(2)
    st.markdown(card("Coeficiente Global", round(global_clust, 6), "Média do coeficiente de todos os nós"), unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)
    i = 1
    for label, node in selected_nodes:
        if node is not None:
            clust = nx.clustering(G_sub, node)
            acc = G_sub.nodes[node].get('accident_count', 0)
            degree = G_sub.degree[node]
            edges = list(G_sub.edges(node, data=True))
            street_names = set()

            for u, v, data in edges:
                name = data.get('name')
                if name:
                    if isinstance(name, list):
                        street_names.update(name)
                    else:
                        street_names.add(name)

            if not street_names:
                street_names_display = "(sem nome disponível)"
            else:
                street_names_display = ", ".join(sorted(street_names))

            if i % 3 == 0:
                col3.markdown(card(f"{label}", round(clust, 4), f"Ruas: {street_names_display} ({acc} Acidentes)"), unsafe_allow_html=True)
            elif i % 2 == 0:
                col2.markdown(card(f"{label}", round(clust, 4), f"Ruas: {street_names_display} ({acc} Acidentes)"), unsafe_allow_html=True)
            else:
                col1.markdown(card(f"{label}", round(clust, 4), f"Ruas: {street_names_display} ({acc} Acidentes)"), unsafe_allow_html=True)
            i+=1

    st.markdown("#### Plot dos nós no mapa")
    st.image(img_path + "coef_clustering_map.png", width=width)

elif page == "Componentes Conectados":
    # componentes conectados ---------------
    st.subheader("Componentes Conectados")

    st.markdown("""
                O grafo muito bem conectado, com poucos nós ficando de fora, pois eles representariam trechos sem conexão com as ruas, e provavelemte com nenhum acidente.
                Essa rede é mais conectada fracamente, com poucos nós ficando de fora em relação ao componente fortemente conectado, pois eles representariam uma rua de mão única, com a direção deles sendo ignorada pelo fracamente conectado.
                """)

    scc = list(nx.strongly_connected_components(G))
    wcc = list(nx.weakly_connected_components(G))

    col1, col2 = st.columns(2)
    col1.markdown(card("Componentes Fortemente Conectados (SCC)", len(scc)), unsafe_allow_html=True)
    col2.markdown(card("Maior SCC", f"{len(max(scc, key=len))} nós"), unsafe_allow_html=True)

    col1.markdown(card("Componentes Fracamente Conectados (WCC)", len(wcc)), unsafe_allow_html=True)
    col2.markdown(card("Maior WCC", f"{len(max(wcc, key=len))} nós"),unsafe_allow_html=True)

    st.markdown("#### Plot dos componentes no mapa")
    st.image(img_path + "scc_wcc_map.png", width=width)
elif page == "Medidas de Centralidade":
    # top 5 por centralidade
    st.subheader("Medidas de Centralidade")

    st.markdown("""
                As medidas trabalhadas serão:
                - Eingenvector
                - Degree
                - Closeness 
                - Betweenness
                - Contagem de acidentes
                """)

    medida = st.selectbox(
        "Medidas",
        [
            "Eigenvector Centrality",
            "Degree Centrality",
            "Closeness Centrality",
            "Betweenness Centrality",
            "Nós com mais acidentes",
            "Maiores Centralidades e Acidentes"
        ]
    )

    def show_map(coords, col):
        lat, lon = coords
        iframe_url = f'''
            <div style="max-width: 100%; overflow: hidden;">
            <iframe 
                src="https://maps.google.com/maps?q={lat},{lon}&z=16&output=embed"
                width="100%" height="400" style="border:0; max-width: 100%;" 
                allowfullscreen="" loading="lazy"
                referrerpolicy="no-referrer-when-downgrade">
            </iframe>
            </div>
            '''
        col.markdown(iframe_url, unsafe_allow_html=True)

    def show_img_and_maps(img, coords,
                          sel_box= "Top 5 nós",
                          options= ["Top 1", "Top 2", "Top 3", "Top 4", "Top 5"], 
                          width = 650):
        col1, col2 = st.columns([4, 3])
        col1.image(img, width=width)
        top = col2.selectbox(
            sel_box,
            options
        )
        if top == options[0]:
            show_map(coords[0], col2)
        elif top == options[1]:
            show_map(coords[1], col2)
        elif top == options[2]:
            show_map(coords[2], col2)
        elif top == options[3]:
            show_map(coords[3], col2)
        elif top == options[4]:
            show_map(coords[4], col2)


    if medida == "Eigenvector Centrality":
        st.subheader("Eigenvector Centrality")

        coords = [
            (40.620153, -73.940809),
            (40.619592, -73.941328),
            (40.619765, -73.941620),
            (40.618593, -73.942416),
            (40.621164, -73.939991)
        ]

        show_img_and_maps(img_path+"top_nodes_eigenvector.png", coords)


    elif medida == "Degree Centrality":
        st.markdown("### Degree Centrality")

        coords = [
            (40.543242, -74.197311),
            (40.546135, -74.174127),
            (40.619908, -73.911387),
            (40.590118, -73.974167),
            (40.547835, -74.220359)
        ]

        show_img_and_maps(img_path + "top_nodes_degree.png", coords)

    elif medida == "Closeness Centrality":
        st.markdown("### Closeness Centrality")

        coords = [
            (40.610020, -74.034222),
            (40.601903, -74.060447),
            (40.644826, -74.017427),
            (40.604399, -74.068982),
            (40.644732, -74.017662)
        ]

        show_img_and_maps(img_path + "top_nodes_closeness.png", coords)

    elif medida == "Betweenness Centrality":
        st.markdown("### Betweenness Centrality")

        coords = [
            (40.644732, -74.017662),
            (40.630924, -74.016711),
            (40.610248, -74.033362),
            (40.604252, -74.069412),
            (40.603693, -74.067901)
        ]

        show_img_and_maps(img_path + "top_nodes_betweenness.png", coords)

    elif medida == "Nós com mais acidentes":
        st.markdown("### Nós com mais acidentes")

        coords = [
            (40.610432, -74.035647),
            (40.604608, -74.055336),
            (40.651923, -73.865963),
            (40.643116, -73.875650),
            (40.695966, -73.984590)
        ]

        show_img_and_maps(img_path + "top_nodes_accidents.png", coords)

    elif medida == "Maiores Centralidades e Acidentes":
        # maiores centralidades
        st.subheader("Maiores Centralidades e Taxa de Acidentes")

        coords = [
            (40.620153, -73.940809),
            (40.543242, -74.197311),
            (40.610020, -74.034222),
            (40.644732, -74.017662),
            (40.610432, -74.035647),
        ]

        options = [
            "Eigenvector",
            "Degree",
            "Closeness",
            "Betweenness",
            "Acidentes"
        ]

        show_img_and_maps(img_path + "centralities_with_accidents.png", coords,
                          sel_box = "Nós de maior valor",
                          options = options)

    # st.header("Visualização de um Subgrafo com PyVis")
    # draw_graph_pyvis(G_acidentes_brooklyn)

st.markdown("<script>window.scrollTo(0, 0);</script>", unsafe_allow_html=True)