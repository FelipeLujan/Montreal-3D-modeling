import os
import json
import re

BASE_DIR = r"C:\Users\Felipe\Documents\coding\montreal"

PILOT_BLOCKS = [
    {
        "block_id": "MTL-VM-0001",
        "name": "Place d'Armes (Park in front of Notre-Dame Basilica)",
        "street_address": "500 Place d'Armes, Montréal, QC H2Y 2W2",
        "lat": 45.50472,
        "lon": -73.55661,
        "bbox": "45.5041,-73.5574,45.5053,-73.5558",
        "archetype": "Civic Square / Monument Park (Maisonneuve Monument, Trees, Lamps, Granite Paving)",
        "streetview_points": [
            {"label": "Center_South_to_Basilica", "lat": 45.50472, "lon": -73.55661, "heading": 145},
            {"label": "North_to_BMO_Dome", "lat": 45.50472, "lon": -73.55661, "heading": 325},
            {"label": "East_to_Aldred_Tower", "lat": 45.50465, "lon": -73.55625, "heading": 65},
            {"label": "West_to_500_Place_dArmes", "lat": 45.50455, "lon": -73.55695, "heading": 245}
        ]
    },
    {
        "block_id": "MTL-VM-0002",
        "name": "Basilique Notre-Dame & Séminaire de Saint-Sulpice Block",
        "street_address": "110 Rue Notre-Dame Ouest, Montréal, QC H2Y 1T1",
        "lat": 45.50448,
        "lon": -73.55605,
        "bbox": "45.5037,-73.5568,45.5049,-73.5551",
        "archetype": "Gothic Revival Cathedral + 17th-Century Cut-Stone Seminary & Forecourt Wall",
        "streetview_points": [
            {"label": "Basilica_West_Towers_Facade", "lat": 45.50462, "lon": -73.55635, "heading": 140},
            {"label": "Seminaire_Saint_Sulpice_Clock", "lat": 45.50435, "lon": -73.55670, "heading": 150},
            {"label": "Corner_NotreDame_SaintSulpice", "lat": 45.50478, "lon": -73.55595, "heading": 195},
            {"label": "Rue_SaintSulpice_Side_Wall", "lat": 45.50425, "lon": -73.55555, "heading": 240}
        ]
    },
    {
        "block_id": "MTL-VM-0003",
        "name": "Bank of Montreal Main Branch (Dome) & Place d'Armes North",
        "street_address": "119 Rue Saint-Jacques, Montréal, QC H2Y 1L6",
        "lat": 45.50528,
        "lon": -73.55712,
        "bbox": "45.5048,-73.5579,45.5058,-73.5563",
        "archetype": "Neoclassical Pantheon-Domed Bank + Beaux-Arts Stone Facades",
        "streetview_points": [
            {"label": "BMO_Portico_South_View", "lat": 45.50495, "lon": -73.55685, "heading": 325},
            {"label": "Rue_SaintJacques_East", "lat": 45.50515, "lon": -73.55650, "heading": 290},
            {"label": "Rue_SaintJacques_West", "lat": 45.50480, "lon": -73.55740, "heading": 20},
            {"label": "Rear_Rue_SaintAntoine", "lat": 45.50565, "lon": -73.55745, "heading": 145}
        ]
    },
    {
        "block_id": "MTL-VM-0004",
        "name": "Édifice Aldred & New York Life Building (Place d'Armes East)",
        "street_address": "507 Place d'Armes, Montréal, QC H2Y 2W8",
        "lat": 45.50495,
        "lon": -73.55575,
        "bbox": "45.5044,-73.5563,45.5055,-73.5550",
        "archetype": "Art Deco Stepped Limestone Tower (23-story) + Red Sandstone Romanesque Revival",
        "streetview_points": [
            {"label": "Aldred_ArtDeco_Facade", "lat": 45.50480, "lon": -73.55615, "heading": 65},
            {"label": "NY_Life_Red_Sandstone_Corner", "lat": 45.50510, "lon": -73.55635, "heading": 110},
            {"label": "Rue_NotreDame_Side", "lat": 45.50485, "lon": -73.55585, "heading": 350},
            {"label": "Coté_Place_dArmes_East", "lat": 45.50525, "lon": -73.55605, "heading": 140}
        ]
    },
    {
        "block_id": "MTL-VM-0005",
        "name": "500 Place d'Armes Tower (Banque Canadienne Nationale)",
        "street_address": "500 Place d'Armes (West Side), Montréal, QC H2Y 2W2",
        "lat": 45.50425,
        "lon": -73.55735,
        "bbox": "45.5037,-73.5581,45.5048,-73.5567",
        "archetype": "International Style Modernist High-Rise + Plinth",
        "streetview_points": [
            {"label": "500_Place_dArmes_East_Plaza", "lat": 45.50455, "lon": -73.55695, "heading": 240},
            {"label": "Corner_SaintJacques_Place_dArmes", "lat": 45.50475, "lon": -73.55730, "heading": 190},
            {"label": "Corner_NotreDame_Ouest", "lat": 45.50410, "lon": -73.55690, "heading": 290},
            {"label": "West_Side_Rue_SaintFrancoisXavier", "lat": 45.50405, "lon": -73.55785, "heading": 60}
        ]
    },
    {
        "block_id": "MTL-VM-0006",
        "name": "Rue Saint-Jacques Financial Canyon (West of Place d'Armes)",
        "street_address": "240 Rue Saint-Jacques, Montréal, QC H2Y 1L9",
        "lat": 45.50385,
        "lon": -73.55845,
        "bbox": "45.5032,-73.5593,45.5045,-73.5576",
        "archetype": "Early 20th-Century Beaux-Arts Financial Palaces (Royal Bank Tower)",
        "streetview_points": [
            {"label": "Royal_Bank_Tower_Portal", "lat": 45.50365, "lon": -73.55875, "heading": 145},
            {"label": "SaintJacques_East_Canyon", "lat": 45.50415, "lon": -73.55810, "heading": 230},
            {"label": "Rue_NotreDame_South_Side", "lat": 45.50345, "lon": -73.55805, "heading": 320},
            {"label": "Corner_Rue_SaintPierre", "lat": 45.50335, "lon": -73.55910, "heading": 55}
        ]
    },
    {
        "block_id": "MTL-VM-0007",
        "name": "Rue Saint-Sulpice & Cours Le Royer Historic Block",
        "street_address": "430 Rue Saint-Sulpice, Montréal, QC H2Y 2V5",
        "lat": 45.50390,
        "lon": -73.55505,
        "bbox": "45.5033,-73.5558,45.5045,-73.5543",
        "archetype": "19th-Century Old Montreal Cut-Stone Warehouse & Residential Conversions",
        "streetview_points": [
            {"label": "Rue_SaintSulpice_Facade", "lat": 45.50410, "lon": -73.55545, "heading": 115},
            {"label": "Cours_Le_Royer_Courtyard", "lat": 45.50380, "lon": -73.55485, "heading": 35},
            {"label": "Corner_Rue_SaintPaul", "lat": 45.50345, "lon": -73.55495, "heading": 330},
            {"label": "Corner_Rue_DeBresoles", "lat": 45.50435, "lon": -73.55525, "heading": 165}
        ]
    },
    {
        "block_id": "MTL-VM-0008",
        "name": "Rue Saint-Paul Ouest & Rue Saint-François-Xavier Block",
        "street_address": "200 Rue Saint-Paul Ouest, Montréal, QC H2Y 1Z9",
        "lat": 45.50315,
        "lon": -73.55595,
        "bbox": "45.5025,-73.5568,45.5037,-73.5551",
        "archetype": "Cobblestone Commercial Street + Historic Limestone & Mansard Roofs",
        "streetview_points": [
            {"label": "Rue_SaintPaul_Cobblestone_East", "lat": 45.50325, "lon": -73.55565, "heading": 235},
            {"label": "Rue_SaintPaul_Cobblestone_West", "lat": 45.50285, "lon": -73.55635, "heading": 55},
            {"label": "Corner_SaintFrancoisXavier", "lat": 45.50310, "lon": -73.55665, "heading": 120},
            {"label": "Rue_du_SaintSacrement", "lat": 45.50355, "lon": -73.55615, "heading": 160}
        ]
    },
    {
        "block_id": "MTL-VM-0009",
        "name": "Vieux-Séminaire / Rue Notre-Dame Ouest & Rue McGill",
        "street_address": "260 Rue Notre-Dame Ouest, Montréal, QC H2Y 1T6",
        "lat": 45.50265,
        "lon": -73.55775,
        "bbox": "45.5020,-73.5586,45.5033,-73.5569",
        "archetype": "Victorian Commercial Stone Block + Ground-Floor Cafes",
        "streetview_points": [
            {"label": "NotreDame_Ouest_Front", "lat": 45.50295, "lon": -73.55785, "heading": 145},
            {"label": "Corner_Rue_SaintPierre", "lat": 45.50260, "lon": -73.55835, "heading": 90},
            {"label": "Rue_SaintPaul_Rear", "lat": 45.50225, "lon": -73.55735, "heading": 325},
            {"label": "Rue_SaintJean_Side", "lat": 45.50285, "lon": -73.55715, "heading": 240}
        ]
    },
    {
        "block_id": "MTL-VM-0010",
        "name": "Palais des Congrès (Colorful Glass Facade) & Place Jean-Paul-Riopelle",
        "street_address": "1001 Place Jean-Paul-Riopelle, Montréal, QC H2Z 1H5",
        "lat": 45.50595,
        "lon": -73.55945,
        "bbox": "45.5051,-73.5606,45.5068,-73.5583",
        "archetype": "Modern Convention Center Multi-Colored Translucent Glass + Public Plaza",
        "streetview_points": [
            {"label": "Place_Riopelle_Colored_Glass", "lat": 45.50555, "lon": -73.55985, "heading": 55},
            {"label": "Avenue_Viger_North_Entrance", "lat": 45.50645, "lon": -73.55915, "heading": 150},
            {"label": "Rue_SaintAntoine_South_Facade", "lat": 45.50525, "lon": -73.55915, "heading": 330},
            {"label": "Rue_SaintUrbain_East_Side", "lat": 45.50625, "lon": -73.55845, "heading": 240}
        ]
    },
    {
        "block_id": "MTL-VM-0011",
        "name": "World Trade Centre Montreal (Centre de Commerce Mondial)",
        "street_address": "747 Rue du Square-Victoria, Montréal, QC H2Y 3Y9",
        "lat": 45.50245,
        "lon": -73.56055,
        "bbox": "45.5017,-73.5616,45.5032,-73.5595",
        "archetype": "Full-Block Glass Atrium Integrating Historic Victorian Stone Facades",
        "streetview_points": [
            {"label": "Square_Victoria_West_Entrance", "lat": 45.50215, "lon": -73.56125, "heading": 65},
            {"label": "Rue_SaintAntoine_North_Wall", "lat": 45.50295, "lon": -73.56065, "heading": 145},
            {"label": "Rue_SaintJacques_South_Facades", "lat": 45.50225, "lon": -73.56015, "heading": 325},
            {"label": "Corner_Rue_SaintPierre", "lat": 45.50275, "lon": -73.55965, "heading": 235}
        ]
    },
    {
        "block_id": "MTL-VM-0012",
        "name": "Square Victoria (Metro Guimard Entrance & Park)",
        "street_address": "700 Rue du Square-Victoria, Montréal, QC H2Y 2J1",
        "lat": 45.50185,
        "lon": -73.56185,
        "bbox": "45.5011,-73.5628,45.5026,-73.5609",
        "archetype": "Urban Tree Plaza + Art Nouveau Paris Metro Entrance + Queen Victoria Statue",
        "streetview_points": [
            {"label": "Guimard_Metro_Entrance", "lat": 45.50210, "lon": -73.56155, "heading": 225},
            {"label": "Queen_Victoria_Monument_South", "lat": 45.50145, "lon": -73.56215, "heading": 45},
            {"label": "Square_Victoria_East_Walk", "lat": 45.50180, "lon": -73.56145, "heading": 310},
            {"label": "Square_Victoria_West_Walk", "lat": 45.50195, "lon": -73.56225, "heading": 130}
        ]
    },
    {
        "block_id": "MTL-VM-0013",
        "name": "Courthouse Block (Palais de Justice de Montréal)",
        "street_address": "1 Rue Notre-Dame Est, Montréal, QC H2Y 1B6",
        "lat": 45.50645,
        "lon": -73.55465,
        "bbox": "45.5057,-73.5556,45.5072,-73.5537",
        "archetype": "Brutalist/Modernist Judicial Complex + Ernest-Cormier Neoclassical Building",
        "streetview_points": [
            {"label": "Rue_NotreDame_Main_Plaza", "lat": 45.50605, "lon": -73.55455, "heading": 325},
            {"label": "Edifice_Ernest_Cormier_Columns", "lat": 45.50675, "lon": -73.55385, "heading": 240},
            {"label": "Rue_SaintAntoine_North", "lat": 45.50695, "lon": -73.55495, "heading": 145},
            {"label": "Boulevard_SaintLaurent_West", "lat": 45.50595, "lon": -73.55535, "heading": 65}
        ]
    },
    {
        "block_id": "MTL-VM-0014",
        "name": "Place Jacques-Cartier & Hôtel de Ville (City Hall)",
        "street_address": "275 Rue Notre-Dame Est, Montréal, QC H2Y 1C6",
        "lat": 45.50865,
        "lon": -73.55385,
        "bbox": "45.5078,-73.5548,45.5095,-73.5529",
        "archetype": "Second Empire City Hall + Sloping Pedestrian Plaza & Terraces",
        "streetview_points": [
            {"label": "Hotel_de_Ville_Front_Facade", "lat": 45.50855, "lon": -73.55415, "heading": 65},
            {"label": "Nelson_Monument_Top_of_Square", "lat": 45.50835, "lon": -73.55425, "heading": 145},
            {"label": "Place_JacquesCartier_Terraces", "lat": 45.50795, "lon": -73.55365, "heading": 325},
            {"label": "Corner_Rue_SaintPaul_Est", "lat": 45.50765, "lon": -73.55325, "heading": 320}
        ]
    },
    {
        "block_id": "MTL-VM-0015",
        "name": "Pointe-à-Callière Museum & Place Royale",
        "street_address": "350 Place Royale, Montréal, QC H2Y 3Y5",
        "lat": 45.50275,
        "lon": -73.55415,
        "bbox": "45.5021,-73.5550,45.5034,-73.5533",
        "archetype": "Triangular Contemporary Stone/Steel Museum + Cobblestone Square",
        "streetview_points": [
            {"label": "Pointe_a_Calliere_Prow_Tower", "lat": 45.50245, "lon": -73.55445, "heading": 45},
            {"label": "Place_Royale_Custom_House", "lat": 45.50295, "lon": -73.55415, "heading": 225},
            {"label": "Rue_de_la_Commune_Waterfront", "lat": 45.50255, "lon": -73.55375, "heading": 310},
            {"label": "Rue_McGill_Corner_Approach", "lat": 45.50215, "lon": -73.55485, "heading": 55}
        ]
    },
    # Wave 1 Expansion: Blocks MTL-VM-0016 through MTL-VM-0020
    {
        "block_id": "MTL-VM-0016",
        "name": "Rue Saint-Paul Est & Rue Saint-Gabriel Historic Block (Place Vauquelin & Vieux Palais)",
        "street_address": "Place Vauquelin / 275 Rue Notre-Dame Est, Montréal, QC H2Y 1C6",
        "lat": 45.50785,
        "lon": -73.55440,
        "bbox": "45.5071,-73.5552,45.5086,-73.5536",
        "archetype": "Cut-Stone Commercial Rows, Historic Courtyards, Place Vauquelin & Neoclassical Court Facades",
        "streetview_points": [
            {"label": "Place_Vauquelin_West", "lat": 45.50855, "lon": -73.55485, "heading": 85},
            {"label": "Rue_SaintGabriel_North", "lat": 45.50745, "lon": -73.55425, "heading": 30},
            {"label": "Rue_NotreDameEst_South", "lat": 45.50825, "lon": -73.55420, "heading": 130},
            {"label": "Rue_SaintPaulEst_South", "lat": 45.50735, "lon": -73.55395, "heading": 235}
        ]
    },
    {
        "block_id": "MTL-VM-0017",
        "name": "Château Ramezay & Rue Notre-Dame Est Heritage Block",
        "street_address": "280 Rue Notre-Dame Est, Montréal, QC H2Y 1C5",
        "lat": 45.50875,
        "lon": -73.55313,
        "bbox": "45.5080,-73.5539,45.5095,-73.5523",
        "archetype": "18th-Century Vaulted Fieldstone Residence, French Colonial Gardens, Cut-Stone Row Facades",
        "streetview_points": [
            {"label": "Chateau_Ramezay_Front_Facade", "lat": 45.50865, "lon": -73.55345, "heading": 145},
            {"label": "Rue_NotreDameEst_Approach", "lat": 45.50890, "lon": -73.55295, "heading": 235},
            {"label": "Rue_SaintClaude_North", "lat": 45.50835, "lon": -73.55275, "heading": 325},
            {"label": "Rue_SaintPaulEst_Rear", "lat": 45.50815, "lon": -73.55315, "heading": 55}
        ]
    },
    {
        "block_id": "MTL-VM-0018",
        "name": "Marché Bonsecours (Silver Neoclassical Dome) & Rue Saint-Paul Est",
        "street_address": "350 Rue Saint-Paul Est, Montréal, QC H2Y 1H2",
        "lat": 45.50895,
        "lon": -73.55149,
        "bbox": "45.5082,-73.5524,45.5097,-73.5506",
        "archetype": "Monumental Neoclassical Cut-Stone Market Hall, Central Cast-Iron Silver Dome, Tuscan Portico",
        "streetview_points": [
            {"label": "Marche_Bonsecours_Portico_Dome", "lat": 45.50920, "lon": -73.55175, "heading": 145},
            {"label": "Rue_SaintPaulEst_West_Approach", "lat": 45.50880, "lon": -73.55210, "heading": 60},
            {"label": "Rue_de_la_CommuneEst_Waterfront", "lat": 45.50860, "lon": -73.55115, "heading": 325},
            {"label": "Rue_du_Marche_Bonsecours_East", "lat": 45.50940, "lon": -73.55110, "heading": 235}
        ]
    },
    {
        "block_id": "MTL-VM-0019",
        "name": "Chapelle Notre-Dame-de-Bon-Secours & Rue Bonsecours Block",
        "street_address": "400 Rue Saint-Paul Est, Montréal, QC H2Y 1H4",
        "lat": 45.50979,
        "lon": -73.55107,
        "bbox": "45.5091,-73.5519,45.5105,-73.5501",
        "archetype": "Heritage Stone Sailors' Chapel, Verdigris Copper Spire & Angel, Historic Bonsecours Commercial Facades",
        "streetview_points": [
            {"label": "Chapelle_Bonsecours_Spire_Facade", "lat": 45.50995, "lon": -73.55135, "heading": 140},
            {"label": "Rue_Bonsecours_South_Canyon", "lat": 45.51035, "lon": -73.55140, "heading": 160},
            {"label": "Rue_SaintPaulEst_East_Approach", "lat": 45.50965, "lon": -73.55065, "heading": 240},
            {"label": "Rue_Bonneau_Corner", "lat": 45.51025, "lon": -73.55075, "heading": 210}
        ]
    },
    {
        "block_id": "MTL-VM-0020",
        "name": "Champ-de-Mars & Ancien Hôpital Général Ramparts Block",
        "street_address": "Le Champ-de-Mars, Rue Saint-Antoine Est, Montréal, QC H2Y 1B4",
        "lat": 45.50950,
        "lon": -73.55420,
        "bbox": "45.5086,-73.5552,45.5102,-73.5530",
        "archetype": "Terraced Urban Rampart Park, Excavated 18th-Century Stone Fortification Walls, Civic Escarpment",
        "streetview_points": [
            {"label": "Champ_de_Mars_Metro_South", "lat": 45.51020, "lon": -73.55445, "heading": 150},
            {"label": "Rue_SaintAntoineEst_Ramparts", "lat": 45.50985, "lon": -73.55495, "heading": 120},
            {"label": "Rue_Gosford_Corner", "lat": 45.50925, "lon": -73.55395, "heading": 330},
            {"label": "Terrace_Vauquelin_North", "lat": 45.50895, "lon": -73.55465, "heading": 35}
        ]
    },
    # Wave 2 Expansion: Blocks MTL-VM-0021 through MTL-VM-0025 (Waterfront & Quays)
    {
        "block_id": "MTL-VM-0021",
        "name": "Quai King-Edward & Montreal Science Centre Waterfront",
        "street_address": "2 Rue de la Commune Ouest, Montréal, QC H2Y 4B2",
        "lat": 45.50479,
        "lon": -73.55074,
        "bbox": "45.5036,-73.5520,45.5060,-73.5495",
        "archetype": "Industrial Marine Pier Promenade, Modern Steel/Glass Science Centre Sheds, Granite Wharf Bulkheads",
        "streetview_points": [
            {"label": "Science_Centre_South_Promenade", "lat": 45.50445, "lon": -73.55035, "heading": 330},
            {"label": "Quai_King_Edward_North_Entrance", "lat": 45.50525, "lon": -73.55135, "heading": 145},
            {"label": "Rue_de_la_Commune_Science_Crossing", "lat": 45.50495, "lon": -73.55185, "heading": 110},
            {"label": "Quai_King_Edward_Pier_Tip", "lat": 45.50415, "lon": -73.54965, "heading": 240}
        ]
    },
    {
        "block_id": "MTL-VM-0022",
        "name": "Quai Alexandra & Grand Quai du Port de Montréal (Cruise Terminal & Tower)",
        "street_address": "200 Rue de la Commune Ouest, Montréal, QC H2Y 4B2",
        "lat": 45.50241,
        "lon": -73.55284,
        "bbox": "45.5012,-73.5542,45.5036,-73.5515",
        "archetype": "Modern Marine Cruise Terminal, Stepped Green Wooden Roof Plaza, Contemporary Concrete/Glass Tower",
        "streetview_points": [
            {"label": "Grand_Quai_Terminal_Plaza", "lat": 45.50285, "lon": -73.55235, "heading": 140},
            {"label": "Grand_Quai_Tower_South", "lat": 45.50215, "lon": -73.55165, "heading": 60},
            {"label": "Promenade_du_Grand_Quai_Roof", "lat": 45.50255, "lon": -73.55325, "heading": 105},
            {"label": "Rue_de_la_Commune_Alexandra_Entrance", "lat": 45.50315, "lon": -73.55365, "heading": 135}
        ]
    },
    {
        "block_id": "MTL-VM-0023",
        "name": "Quai Jacques-Cartier & Place Jacques-Cartier Waterfront Entrance",
        "street_address": "Rue de la Commune Est / Quai Jacques-Cartier, Montréal, QC H2Y 1J1",
        "lat": 45.50730,
        "lon": -73.55032,
        "bbox": "45.5062,-73.5516,45.5084,-73.5490",
        "archetype": "Waterfront Timber/Steel Pavilions, Festival Pier Promenade, Granite Edge Quayside, Marina Basin",
        "streetview_points": [
            {"label": "Quai_Jacques_Cartier_Entrance_Pergola", "lat": 45.50745, "lon": -73.55135, "heading": 135},
            {"label": "Rue_de_la_CommuneEst_Quayside", "lat": 45.50775, "lon": -73.55195, "heading": 115},
            {"label": "Quai_Jacques_Cartier_Pier_Center", "lat": 45.50695, "lon": -73.55015, "heading": 235},
            {"label": "Bassin_Jacques_Cartier_Marina", "lat": 45.50655, "lon": -73.55085, "heading": 45}
        ]
    },
    {
        "block_id": "MTL-VM-0024",
        "name": "Bassin Bonsecours, Île Bonsecours & La Grande Roue de Montréal",
        "street_address": "362 Rue de la Commune Est, Montréal, QC H2Y 0B4",
        "lat": 45.50874,
        "lon": -73.54884,
        "bbox": "45.5078,-73.5500,45.5098,-73.5476",
        "archetype": "60m Tubular Steel Ferris Wheel Structure, Historic Island Pavilion, Reflective Basin Water Edge",
        "streetview_points": [
            {"label": "Grande_Roue_Southwest_Waterfront", "lat": 45.50845, "lon": -73.54945, "heading": 45},
            {"label": "Bassin_Bonsecours_North_Boardwalk", "lat": 45.50915, "lon": -73.54985, "heading": 150},
            {"label": "Rue_de_la_CommuneEst_Basin_View", "lat": 45.50935, "lon": -73.55055, "heading": 130},
            {"label": "Ile_Bonsecours_Pavilion_Approach", "lat": 45.50875, "lon": -73.54825, "heading": 240}
        ]
    },
    {
        "block_id": "MTL-VM-0025",
        "name": "Quai de l'Horloge (Old Port Clock Tower) & Rue Berri-Commune",
        "street_address": "1 Rue Quai de l'Horloge, Montréal, QC H2L 0E2",
        "lat": 45.51229,
        "lon": -73.54584,
        "bbox": "45.5108,-73.5478,45.5132,-73.5445",
        "archetype": "45m White Beaux-Arts Memorial Clock Tower, Cupola & Gilded Mechanism, Wooden Boardwalk, Beach",
        "streetview_points": [
            {"label": "Clock_Tower_Quayside_South_Approach", "lat": 45.51185, "lon": -73.54635, "heading": 35},
            {"label": "Plage_de_l_Horloge_Boardwalk", "lat": 45.51215, "lon": -73.54685, "heading": 65},
            {"label": "Quai_de_l_Horloge_Road_North", "lat": 45.51085, "lon": -73.54785, "heading": 40},
            {"label": "Gare_Dalhousie_Rue_Berri_Approach", "lat": 45.51045, "lon": -73.54915, "heading": 70}
        ]
    }
]

WAVE3_BLOCKS = [
    {
        "block_id": "MTL-VM-0026",
        "name": "Place d'Youville West & Old Fire Station (Centre d'histoire de Montréal)",
        "street_address": "335 Place d'Youville, Montréal, QC H2Y 2B7",
        "lat": 45.50125,
        "lon": -73.5555,
        "bbox": "45.5005,-73.5565,45.5020,-73.5545",
        "archetype": "Flemish-Gabled Red Brick/Sandstone Firehouse Tower, Obelisk Monument, Linear Cobblestone Square & Historic Warehouses",
        "streetview_points": [
            {"label": "Firehouse_Caserne_Facade", "lat": 45.50119, "lon": -73.55557, "heading": 117, "pano_id": "67sKgiYKev1XAcklLxkU7Q", "date": "2020-11", "copyright": "© Google", "snapped_source": "street:Place d'Youville"},
            {"label": "Place_dYouville_West_Linear_Walk", "lat": 45.50152, "lon": -73.55586, "heading": 111, "pano_id": "yTYax4bz0rT8xXmH6PqDCw", "date": "2022-11", "copyright": "© Google", "snapped_source": "direct"},
            {"label": "Rue_SaintPierre_Canyon", "lat": 45.50073, "lon": -73.55514, "heading": 20, "pano_id": "B5gXxFYi9hg6VCoiWOTOSw", "date": "2020-11", "copyright": "© Google", "snapped_source": "direct"},
            {"label": "Pionniers_Obelisk_North_View", "lat": 45.50181, "lon": -73.55485, "heading": 198, "pano_id": "5oFSK-ONrwLot3zlDQnxUQ", "date": "2020-11", "copyright": "© Google", "snapped_source": "street:Rue du Port"}
        ]
    },
    {
        "block_id": "MTL-VM-0027",
        "name": "Rue McGill & Place d'Youville Waterfront Gateway (Grand Trunk Building)",
        "street_address": "1-100 Rue McGill, Montréal, QC H2Y 2E5",
        "lat": 45.5002,
        "lon": -73.55685,
        "bbox": "45.4994,-73.5578,45.5010,-73.5559",
        "archetype": "Monumental Beaux-Arts Railway Headquarters (Édifice Gerald-Godin), Neoclassical Stone Columns & Wide Transit Boulevard",
        "streetview_points": [
            {"label": "Grand_Trunk_McGill_Front_Facade", "lat": 45.49959, "lon": -73.55712, "heading": 23, "pano_id": "jFabSSU-uA3HPn-Dn97R8Q", "date": "2020-11", "copyright": "© Google", "snapped_source": "direct"},
            {"label": "Rue_McGill_North_Approach", "lat": 45.50062, "lon": -73.55676, "heading": 330, "pano_id": "DSvHrKIUaV1X_C88q67ZTg", "date": "2020-11", "copyright": "© Google", "snapped_source": "street:service"},
            {"label": "Corner_McGill_CommuneOuest", "lat": 45.49946, "lon": -73.55652, "heading": 22, "pano_id": "_DZcqdGTZwhdFWoWi4osgQ", "date": "2022-06", "copyright": "© Google", "snapped_source": "direct"},
            {"label": "Place_dYouville_West_Edge", "lat": 45.50053, "lon": -73.55617, "heading": 122, "pano_id": "vio7Em0ASh9lGvhsbIhwoQ", "date": "2022-11", "copyright": "© Google", "snapped_source": "direct"}
        ]
    },
    {
        "block_id": "MTL-VM-0028",
        "name": "Bota Bota Floating Ferry Spa, Silo No. 5 Grain Elevators & Pointe-du-Moulin Pier",
        "street_address": "Pointe-du-Moulin / Rue de la Commune Ouest & Rue McGill, Montréal, QC H2Y 4B2",
        "lat": 45.4988,
        "lon": -73.5515,
        "bbox": "45.4975,-73.5532,45.5002,-73.5498",
        "archetype": "Monumental Cylindrical Concrete Grain Silos, Overhead Steel Conveyors, Converted Black-and-White Ferry Boat Mooring & Harbor Basin",
        "streetview_points": [
            {"label": "Bota_Bota_Ferry_Water_Mooring", "lat": 45.49976, "lon": -73.55097, "heading": 52, "pano_id": "9tCQoTAcfyt5NJdh6AiP-Q", "date": "2015-07", "copyright": "© Google", "snapped_source": "direct"},
            {"label": "Silo_No5_Pointe_du_Moulin_North", "lat": 45.4989, "lon": -73.55184, "heading": 112, "pano_id": "vgnhB7lUIycpv_R_kcjK6A", "date": "2015-07", "copyright": "© Google", "snapped_source": "direct"},
            {"label": "Quai_des_Eclusiers_Basin_View", "lat": 45.49952, "lon": -73.55229, "heading": 258, "pano_id": "sZ20KYlQ9wYPXwvLROoMhg", "date": "2015-07", "copyright": "© Google", "snapped_source": "direct"},
            {"label": "Rue_de_la_Commune_Harbor_Crossing", "lat": 45.5005, "lon": -73.55257, "heading": 126, "pano_id": "v6ANHC4kbw7ggtPoDpbZtg", "date": "2024-09", "copyright": "© Google", "snapped_source": "street:service"}
        ]
    },
    {
        "block_id": "MTL-VM-0029",
        "name": "Lachine Canal Entrance Locks (Écluse No. 1), Spillway & Quai des Éclusiers",
        "street_address": "Écluse No. 1 du Canal-de-Lachine, Rue Mill / Rue de la Commune Ouest, Montréal, QC H3C 1Y6",
        "lat": 45.4982,
        "lon": -73.5538,
        "bbox": "45.4972,-73.5552,45.4993,-73.5524",
        "archetype": "Cut-Stone Canal Lock Walls, Massive Timber & Steel Miter Gates, Pedestrian Footbridge, Spillway Flume & Basin Waterfront",
        "streetview_points": [
            {"label": "Ecluse_No1_Lock_Gate_West", "lat": 45.49834, "lon": -73.55334, "heading": 31, "pano_id": "8uqbL2Syn1YwvNw4fSetQQ", "date": "2022-06", "copyright": "© Google", "snapped_source": "direct"},
            {"label": "Lachine_Canal_Spillway_Approach", "lat": 45.49788, "lon": -73.55415, "heading": 41, "pano_id": "T8sFlQbsSdwYweIYUCsQJQ", "date": "2022-06", "copyright": "© Google", "snapped_source": "direct"},
            {"label": "Quai_des_Eclusiers_Promenade", "lat": 45.49973, "lon": -73.55394, "heading": 161, "pano_id": "AgzZD-WkW-UaDezMDhN5Ww", "date": "2019-08", "copyright": "© Google", "snapped_source": "street:Rue Normand"},
            {"label": "Rue_Mill_Lock_Bridge_South", "lat": 45.49941, "lon": -73.55489, "heading": 158, "pano_id": "QV-3G0_-wzKx4xlir8Angg", "date": "2022-06", "copyright": "© Google", "snapped_source": "street:Rue McGill"}
        ]
    },
    {
        "block_id": "MTL-VM-0030",
        "name": "Cité du Multimédia & Rue Wellington / Rue King Industrial Loft Corridor",
        "street_address": "111 Rue Duke / 75 Rue Queen, Montréal, QC H3C 2M1",
        "lat": 45.4984,
        "lon": -73.5582,
        "bbox": "45.4974,-73.5595,45.4994,-73.5569",
        "archetype": "Early-20th-Century Brick & Cut-Stone Industrial Tech Lofts, Segmental Arched Factory Windows, Cast-Iron Pillars & Urban Canyon",
        "streetview_points": [
            {"label": "Cite_Multimedia_Main_Portal", "lat": 45.4996, "lon": -73.55843, "heading": 170, "pano_id": "Hkc950MJKS1w6NIfmX4-zg", "date": "2020-11", "copyright": "© Google", "snapped_source": "street:service"},
            {"label": "Rue_Wellington_Industrial_Canyon", "lat": 45.49878, "lon": -73.55853, "heading": 148, "pano_id": "jz1AEgiidavt1BhLL7XqHQ", "date": "2024-09", "copyright": "© Google", "snapped_source": "direct"},
            {"label": "Corner_King_and_Queen", "lat": 45.49972, "lon": -73.55766, "heading": 183, "pano_id": "BDX2XknrRjTAIPzCtfKZsQ", "date": "2020-11", "copyright": "© Google", "snapped_source": "street:Rue Saint-Paul Ouest"},
            {"label": "Rue_Duke_Tech_Corridor", "lat": 45.4998, "lon": -73.55772, "heading": 169, "pano_id": "NCQzgbq7N9uTICuPUyxJPw", "date": "2020-11", "copyright": "© Google", "snapped_source": "street:Rue de Longueuil"}
        ]
    },
    {
        "block_id": "MTL-VM-0031",
        "name": "Chinatown South Gate (Porte de Quartier Chinois Paifang Arch) & Blvd Saint-Laurent / Rue de la Gauchetière",
        "street_address": "Boulevard Saint-Laurent / Rue de la Gauchetière Est, Montréal, QC H2X 1P7",
        "lat": 45.5078,
        "lon": -73.5601,
        "bbox": "45.5068,-73.5612,45.5088,-73.5590",
        "archetype": "Ornate Polychrome Red/Gold Chinese Paifang Ceremonial Archway, Tiered Green Glazed Tile Roof, Sun Yat-sen Plaza & Pedestrian Shophouses",
        "streetview_points": [
            {"label": "South_Chinatown_Paifang_Arch", "lat": 45.507, "lon": -73.5603, "heading": 60, "pano_id": "IuatgJyNJifnVwlgSEQyng", "date": "2020-11", "copyright": "© Google", "snapped_source": "street:Allée Isaac"},
            {"label": "Place_Sun_Yat_Sen_Plaza", "lat": 45.50788, "lon": -73.56068, "heading": 80, "pano_id": "0OZeqahen2T4H3vcRSZdKQ", "date": "2022-11", "copyright": "© Google", "snapped_source": "street:Rue Clark"},
            {"label": "Rue_Gauchetiere_Pedestrian_Mall", "lat": 45.50758, "lon": -73.55881, "heading": 302, "pano_id": "wHzu5r2Xg3ooZhMRBFhaqA", "date": "2022-11", "copyright": "© Google", "snapped_source": "street:Boulevard Saint-Laurent"},
            {"label": "Blvd_SaintLaurent_Chinatown_Axis", "lat": 45.50773, "lon": -73.56036, "heading": 13, "pano_id": "CWJzMDEVm43RTw2j7DH8fQ", "date": "2022-11", "copyright": "© Google", "snapped_source": "street:Rue Clark"}
        ]
    },
    {
        "block_id": "MTL-VM-0032",
        "name": "Rue Saint-Denis & Rue Saint-Antoine Est / Bonsecours North Escarpment",
        "street_address": "Rue Saint-Denis / Rue Saint-Antoine Est, Montréal, QC H2X 1K9",
        "lat": 45.5106,
        "lon": -73.5532,
        "bbox": "45.5098,-73.5543,45.5115,-73.5521",
        "archetype": "Greystone Victorian Commercial Facades, Sloping Escarpment Streetscape, Cut-Stone Retaining Walls & Civic Perimeter",
        "streetview_points": [
            {"label": "Rue_SaintDenis_North_Canyon", "lat": 45.51075, "lon": -73.55319, "heading": 288, "pano_id": "5voxdpb0_zkQd-FchKo4hw", "date": "2022-08", "copyright": "© Google", "snapped_source": "direct"},
            {"label": "Rue_SaintAntoineEst_Escarpment", "lat": 45.51048, "lon": -73.55405, "heading": 115, "pano_id": "A1r5ELoNDwItquFa3IiuPg", "date": "2020-11", "copyright": "© Google", "snapped_source": "direct"},
            {"label": "Rue_Berri_Bonsecours_Link", "lat": 45.511, "lon": -73.55302, "heading": 108, "pano_id": "vn4W2iUMAkYPq-YyZY3PqQ", "date": "2022-08", "copyright": "© Google", "snapped_source": "direct"},
            {"label": "Champ_de_Mars_East_Edge", "lat": 45.51004, "lon": -73.55373, "heading": 288, "pano_id": "2iWvk47E9upyNBEARCZE2w", "date": "2020-11", "copyright": "© Google", "snapped_source": "direct"}
        ]
    },
    {
        "block_id": "MTL-VM-0033",
        "name": "Place Gare-Viger (Château Viger Castle Hotel) & Rue Berri / Rue Saint-Antoine Est",
        "street_address": "700 Rue Saint-Antoine Est, Montréal, QC H2Y 1A6",
        "lat": 45.5122,
        "lon": -73.5526,
        "bbox": "45.5114,-73.5537,45.5130,-73.5515",
        "archetype": "Monumental Châteauesque / Romanesque Revival Red Brick & Turreted Castle Hotel, Copper Mansards, Circular Corner Towers & Courtyard Plaza",
        "streetview_points": [
            {"label": "Chateau_Gare_Viger_Main_Turret", "lat": 45.51197, "lon": -73.55301, "heading": 40, "pano_id": "vOdDp9pjGafzmhujIisTYQ", "date": "2019-06", "copyright": "© Google", "snapped_source": "street:service"},
            {"label": "Place_Gare_Viger_Courtyard", "lat": 45.51265, "lon": -73.55195, "heading": 224, "pano_id": "GizjvGu10NcVWwBxmyRAHA", "date": "2020-09", "copyright": "© Google", "snapped_source": "street:Rue Saint-Hubert"},
            {"label": "Rue_Berri_Viger_Frontage", "lat": 45.51175, "lon": -73.55313, "heading": 24, "pano_id": "H04KbHTYWsQORMSUByY4rg", "date": "2019-08", "copyright": "© Google", "snapped_source": "direct"},
            {"label": "Avenue_Viger_Est_North_Wall", "lat": 45.51272, "lon": -73.55219, "heading": 208, "pano_id": "ij_4ZVTu3MUOAyjUrm-BHQ", "date": "2020-09", "copyright": "© Google", "snapped_source": "direct"}
        ]
    },
    {
        "block_id": "MTL-VM-0034",
        "name": "Faubourg Québec & Gare Dalhousie Historic Square (Rue Notre-Dame Est / Rue Dalhousie)",
        "street_address": "200 Rue Berri / 417 Rue Notre-Dame Est, Montréal, QC H2Y 1C9",
        "lat": 45.5117,
        "lon": -73.5508,
        "bbox": "45.5108,-73.5519,45.5126,-73.5497",
        "archetype": "1884 Historic Cut-Stone Railway Terminal (Gare Dalhousie), Tree-Lined Urban Square, Historic Brick Warehouse Conversions & Waterfront Bridge Edge",
        "streetview_points": [
            {"label": "Gare_Dalhousie_Portico_Front", "lat": 45.51171, "lon": -73.5516, "heading": 119, "pano_id": "yIHusQh2yYI83_p44kOMKg", "date": "2009-04", "copyright": "© Google", "snapped_source": "direct"},
            {"label": "Square_Dalhousie_Park_Walk", "lat": 45.51232, "lon": -73.55124, "heading": 168, "pano_id": "6bB6J_usJE0Rquz2fQnNzg", "date": "2022-11", "copyright": "© Google", "snapped_source": "street:Rue Notre-Dame Est"},
            {"label": "Rue_NotreDameEst_Railway_Bridge", "lat": 45.51107, "lon": -73.55054, "heading": 342, "pano_id": "0L4rpAq5qM47-WajzOZhDQ", "date": "2019-06", "copyright": "© Google", "snapped_source": "street:Rue Berri"},
            {"label": "Rue_Dalhousie_South_Approach", "lat": 45.51109, "lon": -73.55005, "heading": 340, "pano_id": "ZKEbcro11Ey3Z_6wAwD9-w", "date": "2022-08", "copyright": "© Google", "snapped_source": "direct"}
        ]
    },
    {
        "block_id": "MTL-VM-0035",
        "name": "Cité du Havre Peninsula, Parc de Dieppe & Habitat 67 Waterfront Vista",
        "street_address": "2600 Avenue Pierre-Dupuy, Montréal, QC H3C 3R6",
        "lat": 45.502,
        "lon": -73.5435,
        "bbox": "45.4980,-73.5460,45.5070,-73.5410",
        "archetype": "Iconic Moshe Safdie Brutalist Interlocking Prefab Concrete Modular Housing Cubes, Cantilevered Terraces, Riprap Peninsula Shoreline & Harbor View",
        "streetview_points": [
            {"label": "Habitat_67_Modular_Cubes_Front", "lat": 45.50112, "lon": -73.54426, "heading": 161, "pano_id": "MvQzx_W_15uAzsRIZrrfJw", "date": "2025-06", "copyright": "© Google", "snapped_source": "street:service"},
            {"label": "Avenue_Pierre_Dupuy_North_Approach", "lat": 45.5014, "lon": -73.54423, "heading": 298, "pano_id": "WSgRzBu33AoHoFqnqXCEvw", "date": "2025-06", "copyright": "© Google", "snapped_source": "street:service"},
            {"label": "Parc_de_Dieppe_Tip_Harbor_View", "lat": 45.50468, "lon": -73.54308, "heading": 349, "pano_id": "94CABeGFosQJTCYGOmRXaA", "date": "2025-06", "copyright": "© Google", "snapped_source": "street:Pont de la Concorde"},
            {"label": "Port_Montreal_Water_Channel_Vista", "lat": 45.50368, "lon": -73.54407, "heading": 206, "pano_id": "oGUtwdmxTi6GzLLyewIMlQ", "date": "2025-06", "copyright": "© Google", "snapped_source": "street:Pont de la Concorde"}
        ]
    }
]

PILOT_BLOCKS.extend(WAVE3_BLOCKS)

# Alias ALL_BLOCKS for clarity
ALL_BLOCKS = PILOT_BLOCKS

WAVE1_BLOCK_IDS = {"MTL-VM-0016", "MTL-VM-0017", "MTL-VM-0018", "MTL-VM-0019", "MTL-VM-0020"}
WAVE2_BLOCK_IDS = {"MTL-VM-0021", "MTL-VM-0022", "MTL-VM-0023", "MTL-VM-0024", "MTL-VM-0025"}
WAVE3_BLOCK_IDS = {f"MTL-VM-{i:04d}" for i in range(26, 36)}

DEFAULT_PILOT_STATUSES = {
    "MTL-VM-0001": "COMPLETED (Iter 3 — 96/100)",
    "MTL-VM-0002": "COMPLETED (Iter 2 — 93/100)",
    "MTL-VM-0003": "COMPLETED (Iter 3 — 93/100)",
    "MTL-VM-0004": "COMPLETED (Iter 2 — 92/100)",
    "MTL-VM-0005": "COMPLETED (Iter 3 — 94/100)",
    "MTL-VM-0006": "COMPLETED (Iter 2 — 93/100)",
    "MTL-VM-0007": "COMPLETED (Iter 2 — 93/100)",
    "MTL-VM-0008": "COMPLETED (Iter 3 — 95/100)",
    "MTL-VM-0009": "COMPLETED (Iter 2 — 93/100)",
    "MTL-VM-0010": "COMPLETED (Iter 2 — 92/100)",
    "MTL-VM-0011": "COMPLETED (Iter 2 — 93/100)",
    "MTL-VM-0012": "COMPLETED (Iter 2 — 93/100)",
    "MTL-VM-0013": "COMPLETED (Iter 2 — 93/100)",
    "MTL-VM-0014": "COMPLETED (Iter 2 — 92/100)",
    "MTL-VM-0015": "COMPLETED (Iter 2 — 94/100)",
    "MTL-VM-0016": "COMPLETED (Iter 1 — 94/100)",
    "MTL-VM-0017": "COMPLETED (Iter 1 — 93/100)",
    "MTL-VM-0018": "COMPLETED (Iter 1 — 95/100)",
    "MTL-VM-0019": "COMPLETED (Iter 1 — 94/100)",
    "MTL-VM-0020": "COMPLETED (Iter 1 — 93/100)",
    "MTL-VM-0021": "COMPLETED (Iter 1 — 93/100)",
    "MTL-VM-0022": "COMPLETED (Iter 1 — 94/100)",
    "MTL-VM-0023": "COMPLETED (Iter 1 — 93/100)",
    "MTL-VM-0024": "COMPLETED (Iter 1 — 94/100)",
    "MTL-VM-0025": "COMPLETED (Iter 1 — 95/100)",
}


def make_gmaps_sv_url(lat: float, lon: float, heading: int, pitch: int = 10) -> str:
    return (
        f"https://www.google.com/maps/@?api=1&map_action=pano"
        f"&viewpoint={lat:.5f},{lon:.5f}&heading={heading}&pitch={pitch}&fov=90"
    )


def load_existing_statuses(work_queue_path: str) -> dict:
    statuses = dict(DEFAULT_PILOT_STATUSES)
    if not os.path.exists(work_queue_path):
        return statuses
    try:
        with open(work_queue_path, "r", encoding="utf-8") as f:
            for line in f:
                if not line.startswith("|"):
                    continue
                parts = [p.strip() for p in line.split("|")]
                if len(parts) >= 4:
                    bid_match = re.search(r"MTL-VM-\d{4}", parts[2])
                    if bid_match:
                        bid = bid_match.group(0)
                        raw_status = parts[3].strip().strip("`")
                        if "COMPLETED" in raw_status or "IN_PROGRESS" in raw_status:
                            statuses[bid] = raw_status
    except Exception as e:
        print(f"Warning parsing existing WORK_QUEUE.md: {e}")
    return statuses


def generate_work_queue():
    work_queue_path = os.path.join(BASE_DIR, "WORK_QUEUE.md")
    existing_statuses = load_existing_statuses(work_queue_path)

    queue_records = []
    for b in PILOT_BLOCKS:
        bid = b["block_id"]
        sv_dir = os.path.join(BASE_DIR, "data", "blocks", bid, "streetview")
        os.makedirs(sv_dir, exist_ok=True)
        blend_path = os.path.join(BASE_DIR, "output", "blocks", f"{bid}.blend")
        render_path = os.path.join(BASE_DIR, "output", "renders", f"{bid}_snapshot.png")

        sv_links = []
        for pt in b["streetview_points"]:
            url = make_gmaps_sv_url(pt["lat"], pt["lon"], pt["heading"])
            sv_links.append({
                "label": pt["label"],
                "lat": pt["lat"],
                "lon": pt["lon"],
                "heading": pt["heading"],
                "google_maps_url": url,
                "local_image": os.path.join(sv_dir, f"{pt['label']}.jpg")
            })

        status = existing_statuses.get(bid, "PENDING")

        rec = {
            "block_id": bid,
            "name": b["name"],
            "street_address": b["street_address"],
            "coordinates": f"{b['lat']:.5f}, {b['lon']:.5f}",
            "lat": b["lat"],
            "lon": b["lon"],
            "bbox": b["bbox"],
            "archetype": b["archetype"],
            "status": status,
            "google_maps_streetviews": " | ".join([f"{x['label']}: {x['google_maps_url']}" for x in sv_links]),
            "streetview_nodes": sv_links,
            "streetview_dir": sv_dir,
            "blend_file": blend_path,
            "render_snapshot": render_path,
        }
        queue_records.append(rec)

    md_lines = [
        "# Montreal 3D Reconstruction — Master City Block Work Queue (All 35 Blocks: Pilot + Waves 1, 2 & 3)\n",
        "> [!NOTE]",
        "> **District Overview:** Covers 35 contiguous city blocks (`MTL-VM-0001` through `MTL-VM-0035`) in Old Montreal and the Waterfront ring.",
        "> - **Pilot District (`MTL-VM-0001..0015`):** Place d'Armes anchor square and perimeter blocks (Notre-Dame Basilica, Aldred Tower, Palais des Congrès, Square Victoria, Pointe-à-Callière).",
        "> - **Wave 1 Expansion (`MTL-VM-0016..0020`):** Rue Saint-Paul Est, Château Ramezay, Marché Bonsecours (Silver Dome), Chapelle Notre-Dame-de-Bon-Secours, Champ-de-Mars Ramparts.",
        "> - **Wave 2 Expansion (`MTL-VM-0021..0025`):** Old Port Waterfront & Quays (Quai King-Edward / Science Centre, Quai Alexandra / Grand Quai, Quai Jacques-Cartier, Bassin Bonsecours / La Grande Roue, Quai de l'Horloge Clock Tower).",
        "> - **Wave 3 Expansion (`MTL-VM-0026..0035`):** Place d'Youville West / Fire Station, Rue McGill / Grand Trunk, Bota Bota / Silo No. 5, Lachine Canal Entrance Locks, Cité du Multimédia, Chinatown South Gate Paifang, Rue Saint-Denis Escarpment, Place Gare-Viger, Faubourg Québec / Gare Dalhousie, Cité du Havre / Habitat 67.",
        ">",
        "> Each block contains **4 directional Google Maps Street View camera viewpoints** verified outdoor and snapped to street centerlines.\n",
        "## City Block Work Queue\n",
        "| # | Block ID & Landmark | Status | Street Address | Coordinates (`Lat, Lon`) | Google Maps Street Views (Included Viewpoints) | Street View Images (Local Folder) | Blender File (`.blend`) | Render Snapshot (`.png`) |",
        "| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |"
    ]

    for idx, rec in enumerate(queue_records, start=1):
        bid = rec["block_id"]
        sv_dir_uri = "file:///" + rec["streetview_dir"].replace("\\", "/")
        blend_uri = "file:///" + rec["blend_file"].replace("\\", "/")
        render_uri = "file:///" + rec["render_snapshot"].replace("\\", "/")

        gmaps_bullets = "<br>".join([
            f"• [{pt['label']} ({pt['heading']}°)]({pt['google_maps_url']})"
            for pt in rec["streetview_nodes"]
        ])

        row = (
            f"| **{idx}** | **{bid}**<br>*({rec['name']})* | `{rec['status']}` | {rec['street_address']} "
            f"| `{rec['coordinates']}` | {gmaps_bullets} "
            f"| [{bid}/streetview]({sv_dir_uri}) "
            f"| [{bid}.blend]({blend_uri}) "
            f"| [{bid}_snapshot.png]({render_uri}) |"
        )
        md_lines.append(row)

    md_content = "\n".join(md_lines) + "\n"
    with open(work_queue_path, "w", encoding="utf-8") as f:
        f.write(md_content)

    print(f"Updated WORK_QUEUE.md in {BASE_DIR} with {len(queue_records)} blocks.")


if __name__ == "__main__":
    generate_work_queue()
