import dash
from dash import dcc, html, Input, Output, no_update
import plotly.express as px
import pandas as pd
import geopandas as gpd #panda for geo spatial data
from prophet import Prophet #machine learning model for forecast

#location of each and every district of tamilnadu 
geojson_path = r"TamilNadu.geojson" 
#data set
csv_path = r"TamilNadu_Electricity_Demand_2023_Monthly.csv"  

gdf = gpd.read_file(geojson_path)
df = pd.read_csv(csv_path)

#intitializing 
app = dash.Dash(__name__, external_stylesheets=['https://codepen.io/chriddyp/pen/bWLwgP.css'], suppress_callback_exceptions=True)


custom_css = {
    'main-div': {
        'background-color': '#ceebfd', 
        'padding': '30px',
        'border-radius': '10px',
        'box-shadow': '0 4px 12px rgba(0, 0, 0, 0.1)',
        'color': '#2c3e50',  
        'font-family': 'Arial, sans-serif'
    },
    'header': {
        'text-align': 'center',
        'color': '#2c3e50',
        'font-family': 'Arial, sans-serif',
        'font-weight': '1000',  
        'font-size': '3.5rem',
        'margin-bottom': '20px'
    },
    'description': {
        'text-align': 'center',
        'color': '#34495e',  
        'font-family': 'Arial, sans-serif',
        'font-size': '2rem',
        'margin-bottom': '30px'
    },
    'dropdown': {
        'width': '50%',
        'margin': '0 auto 30px auto',
        'color': '#34495e',
        'background-color': '#fffff',
        'border': '1px solid #ced4da',
        'border-radius': '4px',
        'padding': '8px',
        'box-shadow': '0 2px 4px rgba(0, 0, 0, 0.05)',  
        'font-size': '1.8rem',
        'font-family': 'Arial, sans-serif'
    },
    'graph': {
        'margin-top': '40px',
        'padding': '20px',
        'background-color': '#87cefa',  
        'border-radius': '8px',
        'box-shadow': '0 6px 12px rgba(0, 0, 0, 0.1)'  
    }
}


# Layout of the app
app.layout = html.Div([
    html.H1("TAMILNADU ELECTRICITY BOARD", style=custom_css['header']),
    
    html.P(
        "This dashboard allows you to explore electricity demand across various districts in Tamil Nadu for the year 2023. "
        "You can interact with the map to select a district and view detailed analysis, including forecasts for future electricity "
        "demand. Use the dropdown menus to choose between monthly or quarterly aggregation and different levels of analysis.",
        style=custom_css['description']
    ),
    
 #MAP DECRALATION
    dcc.Graph(id='choropleth-map', style={'height': '800px', 'width': '100%'}),  
    
    html.Div(id='dropdown-container', children=[
        dcc.Dropdown(
            id='detail-dropdown',
            options=[
                {'label': 'Basic Analysis', 'value': 'basic'},
                {'label': 'Intermediate Analysis', 'value': 'intermediate'},
                {'label': 'Detailed Analysis', 'value': 'detailed'}
            ],
            value='basic',
            style=custom_css['dropdown']
        )
    ], style={'visibility': 'hidden'}),  # Hidden dropdown

    html.Div(id='aggregation-dropdown-container', children=[
        dcc.Dropdown(
            id='aggregation-dropdown',
            options=[
                {'label': 'Monthly', 'value': 'monthly'},
                {'label': 'Quarterly', 'value': 'quarterly'}
            ],
            value='monthly',
            style=custom_css['dropdown']
        )
    ], style={'visibility': 'hidden'}),  # Hidden dropdown

    html.Div(id='district-analysis', style=custom_css['graph']),
], style=custom_css['main-div'])

#call back for using the map
@app.callback(
    Output('choropleth-map', 'figure'),
    Input('choropleth-map', 'clickData')
)
def update_map(clickData):
   #current according to each and every district
    df_total = df.groupby('District')['Electricity_Demand_MWh'].sum().reset_index()

    #FULL SCALE MAP RENDER IN THE PAGE
    fig = px.choropleth(df_total,
                        geojson=gdf,
                        locations='District',
                        featureidkey="properties.NAME_2",  # match district  
                        color='Electricity_Demand_MWh',
                        hover_name='District',
                        color_continuous_scale="Blues",  
                        title=None)  

    fig.update_geos(fitbounds="locations", visible=False)
    fig.update_layout(
        paper_bgcolor='rgba(255, 255, 255, 0)', 
        plot_bgcolor='rgba(255, 255, 255, 0)',   
        font=dict(color="#333333"),
        height=800  # Set map height to make it larger
    )
    return fig

# Callback to show dropdowns after district selection
@app.callback(
    [Output('dropdown-container', 'style'),  # Show/hide dropdown
     Output('aggregation-dropdown-container', 'style')],  # Show aggregation dropdown for monthyly and quaterly drop down
    Input('choropleth-map', 'clickData'),#WOKRS LIKE A ONCLICK LISTENER
    prevent_initial_call=True
)
def display_dropdown(clickData):
    if clickData is None:
        return {'visibility': 'hidden'}, {'visibility': 'hidden'}
    
    return {'visibility': 'visible'}, {'visibility': 'visible'}

# Line graph callback for district analysis
@app.callback(
    Output('district-analysis', 'children'),
    [Input('choropleth-map', 'clickData'),
     Input('detail-dropdown', 'value'),
     Input('aggregation-dropdown', 'value')],
    prevent_initial_call=True
)
#FUNCTION FOR ANALYSIS OF DISTRICT
def display_district_analysis(clickData, detail_level, aggregation):
    if clickData is None or detail_level is None or aggregation is None:
        return no_update
    
    district_name = clickData['points'][0]['location']
    
    # Filter data by selected district
    df_district = df[df['District'] == district_name]
    df_district['Date'] = pd.to_datetime(df_district['Month'], format='%b %Y')
   
   #SELECT MONTHLY FOR ANALYSIS IN DROP DOWN IN IF CASE

   #SELECT QUATERLY FOR ANALYSIS IN DROP DOWN IN ELIF
    if aggregation == 'monthly':
        df_prophet = df_district.groupby('Date').sum().reset_index()[['Date', 'Electricity_Demand_MWh']]
    elif aggregation == 'quarterly':
        df_district['Quarter'] = df_district['Date'].dt.to_period('Q')
        df_prophet = df_district.groupby('Quarter')['Electricity_Demand_MWh'].sum().reset_index()
        df_prophet['Quarter'] = df_prophet['Quarter'].astype(str)

    df_prophet.columns = ['ds', 'y']

   #uing prophet for analysis
    model = Prophet()
    model.fit(df_prophet)
    future = model.make_future_dataframe(periods=12, freq='M')
    forecast = model.predict(future)

    #LINE GRAPH 

    #USING DOTTED LINES FOR FORCASTING DATA 2024

    #USING DASH LINE FOR 2023 DATA 

    #yhat_lower---worst case scenario in prophet method

    #yhat_upper---best case scenario in prophet method
    fig = px.line(df_prophet, x='ds', y='y', title=f'ANALYSIS OF {district_name} IN THE YEAR 2023 AND FORCAST IN 2024',
                  labels={'ds': 'Month', 'y': 'Electricity Consumed (MWh)'})
    fig.add_scatter(x=forecast['ds'], y=forecast['yhat'], mode='lines', name='Forecast (2024)', line=dict(dash='dash'))

    if detail_level == 'detailed':
        fig.add_scatter(x=forecast['ds'], y=forecast['yhat_lower'], mode='lines', name='Lower Bound', line=dict(dash='dot'))
        fig.add_scatter(x=forecast['ds'], y=forecast['yhat_upper'], mode='lines', name='Upper Bound', line=dict(dash='dot'))
   
  # THEME
    fig.update_layout(
        paper_bgcolor='#f9fafb', 
        plot_bgcolor='#ffffff',
        font=dict(color="#333333"),
        xaxis_title="Month",
        yaxis_title="Electricity Consumed (MWh)"
    )

    return dcc.Graph(figure=fig, style=custom_css['graph'])

#RUN 
if __name__ == '__main__':
    app.run_server(debug=True)

