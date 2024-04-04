import dash
from dash import dcc, html, Input, Output, State
import dash_leaflet as dl
import pandas as pd
import plotly.express as px
from dash import dash_table
from dash.exceptions import PreventUpdate

path = 'Electric_Vehicle_Population_Data.csv'
df1 = pd.read_csv(path)
df1 = df1.dropna(subset=['Vehicle Location'])
df = df1.head(2500)  # Adjust the number for your needs
df[['lon', 'lat']] = df['Vehicle Location'].str.extract(r'POINT \(([^ ]+) ([^ ]+)\)')
df['lat'] = pd.to_numeric(df['lat'])
df['lon'] = pd.to_numeric(df['lon'])

df_aggregated = df.groupby('Model Year')['VIN (1-10)'].count().reset_index().rename(columns={'VIN (1-10)': 'Count'})
caf_eligibility_counts = df.groupby(['County', 'Clean Alternative Fuel Vehicle (CAFV) Eligibility']).size().unstack(fill_value=0).reset_index()

app = dash.Dash(__name__)

server = app.server

# Define a common style for all titles
title_style = {'textAlign': 'center', 'margin': '20px 0', 'fontSize': '22px'}

app.layout = html.Div([
    html.H1('Electric Vehicle Population Dashboard', style=title_style),
    html.Div([
        html.H2('Select a City:', style=title_style),
        dcc.Dropdown(
            id='city-dropdown',
            options=[{'label': i, 'value': i} for i in df['City'].unique()],
            value=None,  # Default value
            placeholder="Select a city",
        ),
        html.H2('Select Electric Range:', style=title_style),
        dcc.RangeSlider(
            id='range-slider',
            min=df['Electric Range'].min(),
            max=df['Electric Range'].max(),
            value=[df['Electric Range'].min(), df['Electric Range'].max()],
            marks={i: str(i) for i in range(df['Electric Range'].min(), df['Electric Range'].max() + 1, 50)},
        ),
    ], style={'padding': '0 10%', 'marginBottom': '20px'}),
    html.Div([
        dl.Map(center=[47.6097, -122.3331], zoom=9, children=[
            dl.TileLayer(id='tile-layer'),
        ], id='map', style={'width': '1000px', 'height': '500px'}),
    ], style={'textAlign': 'center', 'padding': '20px'}),
    html.H2('EV Registrations Over Time', style=title_style),
    dcc.Graph(id='temporal-analysis'),
    html.Div([
        html.H2('Enter Desired Electric Range:', style=title_style),
        dcc.Input(id='range-input', type='number', value=100, style={'margin': '10px'}),
        dash_table.DataTable(
            id='matching-models-table',
            columns=[
                {'name': 'Model Year', 'id': 'Model Year'},
                {'name': 'Make', 'id': 'Make'},
                {'name': 'Model', 'id': 'Model'},
                {'name': 'Electric Range', 'id': 'Electric Range'}
            ],
            style_table={'height': '300px', 'overflowY': 'auto'},
            data=[]
        )
    ], style={'padding': '20px'}),
    html.H2('CAFV Eligibility and EV Adoption by County', style=title_style),
    dcc.Graph(id='caf-eligibility-impact', figure={}),
    html.Div([
        html.H2('Vehicle Lookup:', style=title_style),
        html.Label("Enter Make:"),
        dcc.Input(id='input-make', type='text', value=''),
        html.Label("Enter Model:"),
        dcc.Input(id='input-model', type='text', value=''),
        html.Button('Submit', id='submit-val', n_clicks=0),
        html.Div(id='container-button-basic')
    ], style={'textAlign': 'center'})
])


@app.callback(
    Output('map', 'children'),
    [Input('city-dropdown', 'value'),
     Input('range-slider', 'value')]
)
def update_map(selected_city, selected_range):
    filtered_df = df.copy()
    if selected_city:
        filtered_df = filtered_df[filtered_df['City'] == selected_city]
    filtered_df = filtered_df[(filtered_df['Electric Range'] >= selected_range[0]) & (filtered_df['Electric Range'] <= selected_range[1])]
    
    markers = [dl.TileLayer()]
    for _, row in filtered_df.iterrows():
        marker = dl.Marker(position=(row['lat'], row['lon']),
                           children=[dl.Tooltip(f"{row['City']}: {row['Electric Range']} range")])
        markers.append(marker)
    return markers

@app.callback(
    Output('temporal-analysis', 'figure'),
    Input('temporal-analysis', 'id')  # This input is not effectively used but keeps the structure for potential dynamic updates
)
def update_graph(_):
    fig = px.line(df_aggregated, x='Model Year', y='Count', markers=True,
                  title='EV Registrations Over Time')
    fig.update_layout(xaxis_title='Model Year', yaxis_title='Number of Registrations',
                      xaxis=dict(type='category'))  # Treat Model Year as a category to avoid interpolation
    return fig

@app.callback(
    Output('matching-models-table', 'data'),
    [Input('range-input', 'value')]
)
def update_table(desired_range):
    filtered_df = df[df['Electric Range'] >= desired_range]
    return filtered_df[['Model Year', 'Make', 'Model', 'Electric Range']].to_dict('records')
@app.callback(
    Output('caf-eligibility-impact', 'figure'),
    Input('city-dropdown', 'value')  # Assuming you might want to filter by city or other criteria
)
def update_caf_impact(_):
    # Ensure column names are correctly referenced
    # Update column names as they appear in your DataFrame
    columns = caf_eligibility_counts.columns[1:]  # Skip the first column which is 'County'
    fig = px.bar(caf_eligibility_counts, x='County', y=columns,
                 title='CAFV Eligibility and EV Adoption by County',
                 labels={'value': 'Number of Vehicles', 'variable': 'CAFV Eligibility Status'})
    return fig
@app.callback(
    Output('container-button-basic', 'children'),
    [Input('submit-val', 'n_clicks')],
    [State('input-make', 'value'),
     State('input-model', 'value')]
)
def update_output(n_clicks, input_make, input_model):
    if n_clicks == 0:
        raise PreventUpdate
    filtered_df = df[(df['Make'].str.lower() == input_make.lower()) & 
                     (df['Model'].str.lower() == input_model.lower())]
    
    if not filtered_df.empty:
        return html.Div([
            html.P(f"Electric Range: {filtered_df['Electric Range'].iloc[0]}"),
            html.P(f"Base MSRP: {filtered_df['Base MSRP'].iloc[0]}"),
            html.P(f"CAFV Eligibility: {filtered_df['Clean Alternative Fuel Vehicle (CAFV) Eligibility'].iloc[0]}"),
        ])
    else:
        return 'No matching records found'



if __name__ == '__main__':
    app.run_server(debug=True)
