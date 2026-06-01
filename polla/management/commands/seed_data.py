from django.core.management.base import BaseCommand
from django.db import transaction
from polla.models import Fase, Estadio, Pais, Jugador, Partido
import datetime
from django.utils import timezone


FASES = [
    (1, 'Fase de Grupos'),
    (2, 'Ronda de 32'),
    (3, 'Ronda de 16'),
    (4, 'Cuartos de Final'),
    (5, 'Semifinal'),
    (6, 'Tercer Puesto'),
    (7, 'Final'),
]

ESTADIOS = [
    'MetLife Stadium - Nueva York/NJ',
    'AT&T Stadium - Dallas',
    'SoFi Stadium - Los Angeles',
    'Hard Rock Stadium - Miami',
    'Mercedes-Benz Stadium - Atlanta',
    "Levi's Stadium - San Francisco",
    'Arrowhead Stadium - Kansas City',
    'NRG Stadium - Houston',
    'Lumen Field - Seattle',
    'Lincoln Financial Field - Filadelfia',
    'Gillette Stadium - Boston',
    'Estadio Azteca - Ciudad de Mexico',
    'Estadio BBVA - Monterrey',
    'Estadio Akron - Guadalajara',
    'BMO Field - Toronto',
    'BC Place - Vancouver',
]

# (nombre, grupo, emoji)
PAISES = [
    ('Mexico', 1, '🇲🇽'), ('Sudafrica', 1, '🇿🇦'), ('Corea del Sur', 1, '🇰🇷'), ('Republica Checa', 1, '🇨🇿'),
    ('Canada', 2, '🇨🇦'), ('Bosnia Herzegovina', 2, '🇧🇦'), ('Qatar', 2, '🇶🇦'), ('Suiza', 2, '🇨🇭'),
    ('Brasil', 3, '🇧🇷'), ('Marruecos', 3, '🇲🇦'), ('Haiti', 3, '🇭🇹'), ('Escocia', 3, '🏴󠁧󠁢󠁳󠁣󠁴󠁿'),
    ('Estados Unidos', 4, '🇺🇸'), ('Paraguay', 4, '🇵🇾'), ('Australia', 4, '🇦🇺'), ('Turquia', 4, '🇹🇷'),
    ('Alemania', 5, '🇩🇪'), ('Curazao', 5, '🇨🇼'), ('Costa de Marfil', 5, '🇨🇮'), ('Ecuador', 5, '🇪🇨'),
    ('Holanda', 6, '🇳🇱'), ('Japon', 6, '🇯🇵'), ('Suecia', 6, '🇸🇪'), ('Tunez', 6, '🇹🇳'),
    ('Belgica', 7, '🇧🇪'), ('Egipto', 7, '🇪🇬'), ('Iran', 7, '🇮🇷'), ('Nueva Zelanda', 7, '🇳🇿'),
    ('Espana', 8, '🇪🇸'), ('Cabo Verde', 8, '🇨🇻'), ('Arabia Saudita', 8, '🇸🇦'), ('Uruguay', 8, '🇺🇾'),
    ('Francia', 9, '🇫🇷'), ('Senegal', 9, '🇸🇳'), ('Irak', 9, '🇮🇶'), ('Noruega', 9, '🇳🇴'),
    ('Argentina', 10, '🇦🇷'), ('Argelia', 10, '🇩🇿'), ('Austria', 10, '🇦🇹'), ('Jordania', 10, '🇯🇴'),
    ('Portugal', 11, '🇵🇹'), ('Congo DR', 11, '🇨🇩'), ('Uzbekistan', 11, '🇺🇿'), ('Colombia', 11, '🇨🇴'),
    ('Inglaterra', 12, '🏴󠁧󠁢󠁥󠁮󠁧󠁿'), ('Croacia', 12, '🇭🇷'), ('Ghana', 12, '🇬🇭'), ('Panama', 12, '🇵🇦'),
]

# id_pais: [(nombre, edad), ...]
JUGADORES = {
    'Mexico': [
        ('Guillermo Ochoa (Portero)', 39), ('Luis Malagon (Portero)', 26), ('Rodolfo Cota (Portero)', 36),
        ('Cesar Montes (Defensa)', 27), ('Jorge Sanchez (Defensa)', 26), ('Johan Vasquez (Defensa)', 25),
        ('Nestor Araujo (Defensa)', 33), ('Jesus Gallardo (Defensa)', 30), ('Kevin Alvarez (Defensa)', 25),
        ('Edson Alvarez (Mediocampista)', 27), ('Luis Romo (Mediocampista)', 29), ('Carlos Rodriguez (Mediocampista)', 26),
        ('Uriel Antuna (Mediocampista)', 27), ('Roberto Alvarado (Mediocampista)', 26), ('Hirving Lozano (Delantero)', 30),
        ('Raul Jimenez (Delantero)', 33), ('Henry Martin (Delantero)', 31), ('Santiago Gimenez (Delantero)', 23),
        ('Alexis Vega (Delantero)', 27), ('Orbelin Pineda (Mediocampista)', 28), ('Fernando Beltran (Mediocampista)', 27),
        ('Julian Quinones (Delantero)', 28), ('Daniel Aguirre (Mediocampista)', 22), ('Gilberto Sepulveda (Defensa)', 28),
        ('Alexis Gutierrez (Mediocampista)', 23), ('Marcelo Flores (Mediocampista)', 22),
    ],
    'Sudafrica': [
        ('Ronwen Williams (Portero)', 32), ('Ricardo Goss (Portero)', 28), ('Sipho Chaine (Portero)', 28),
        ('Khuliso Mudau (Defensa)', 26), ('Nkosinathi Sibisi (Defensa)', 29), ('Aubrey Modiba (Defensa)', 28),
        ('Siyanda Xulu (Defensa)', 33), ('Tercious Malepe (Defensa)', 25), ('Mothobi Mvala (Mediocampista)', 30),
        ('Teboho Mokoena (Mediocampista)', 27), ('Ethan Ntsontso (Mediocampista)', 23), ('Bathusi Aubaas (Mediocampista)', 29),
        ('Keagan Dolly (Delantero)', 31), ('Percy Tau (Delantero)', 30), ('Lyle Foster (Delantero)', 24),
        ('Evidence Makgopa (Delantero)', 24), ('Bongokuhle Hlongwane (Delantero)', 24), ('Bradley Cross (Defensa)', 25),
        ('Zakhele Lepasa (Delantero)', 27), ('Grant Kekana (Defensa)', 31), ('Yusuf Maart (Mediocampista)', 27),
        ('Haashim Domingo (Mediocampista)', 22), ('Bradley Grobler (Delantero)', 35), ('Luke le Roux (Defensa)', 24),
        ('Abbubaker Mobara (Defensa)', 30), ('Siyethemba Sithebe (Mediocampista)', 30),
    ],
    'Corea del Sur': [
        ('Kim Seung-gyu (Portero)', 36), ('Jo Hyeon-woo (Portero)', 33), ('Song Bum-keun (Portero)', 26),
        ('Kim Min-jae (Defensa)', 28), ('Kim Young-gwon (Defensa)', 35), ('Hong Chul (Defensa)', 32),
        ('Seol Young-woo (Defensa)', 24), ('Lee Ki-je (Defensa)', 27), ('Jung Woo-young (Mediocampista)', 33),
        ('Son Heung-min (Delantero)', 32), ('Lee Jae-sung (Mediocampista)', 32), ('Hwang In-beom (Mediocampista)', 28),
        ('Hwang Hee-chan (Delantero)', 28), ('Lee Kang-in (Mediocampista)', 23), ('Cho Gue-sung (Delantero)', 26),
        ('Oh Hyeon-gyu (Delantero)', 23), ('Yang Hyun-jun (Delantero)', 22), ('Bae Jun-ho (Mediocampista)', 22),
        ('Kim Jin-su (Defensa)', 33), ('Lee Jae-ik (Defensa)', 24), ('Hwang Ui-jo (Delantero)', 32),
        ('Kim Gun-hee (Mediocampista)', 24), ('Park Hyun-bin (Portero)', 29), ('Moon Seon-min (Delantero)', 30),
        ('Na Sang-ho (Delantero)', 27), ('Kwon Chang-hoon (Mediocampista)', 30),
    ],
    'Republica Checa': [
        ('Jiri Stanek (Portero)', 28), ('Tomas Vaclik (Portero)', 34), ('Martin Jedlicka (Portero)', 31),
        ('Tomas Holes (Defensa)', 28), ('David Zima (Defensa)', 24), ('Ladislav Krejci (Defensa)', 25),
        ('Jan Boril (Defensa)', 32), ('Vladimir Coufal (Defensa)', 32), ('Ondrej Lingr (Mediocampista)', 25),
        ('Lukas Provod (Mediocampista)', 27), ('Tomas Soucek (Mediocampista)', 29), ('Antonin Barak (Mediocampista)', 29),
        ('Jakub Jankto (Mediocampista)', 28), ('Patrik Schick (Delantero)', 29), ('Adam Hlozek (Delantero)', 22),
        ('Tomas Cvancara (Delantero)', 24), ('Jan Kuchta (Delantero)', 27), ('Pavel Sulc (Mediocampista)', 24),
        ('Michal Sadilek (Mediocampista)', 26), ('Vaclav Cerny (Delantero)', 26), ('David Doudera (Defensa)', 26),
        ('Ales Mateju (Defensa)', 29), ('Martin Vitik (Defensa)', 23), ('Lukas Cerv (Mediocampista)', 24),
        ('Tomas Chory (Delantero)', 27), ('Jakub Pesek (Delantero)', 24),
    ],
    'Canada': [
        ('Maxime Crepeau (Portero)', 30), ('Milan Borjan (Portero)', 36), ('James Pantemis (Portero)', 27),
        ('Alistair Johnston (Defensa)', 25), ('Kamal Miller (Defensa)', 27), ('Steven Vitoria (Defensa)', 36),
        ('Derek Cornelius (Defensa)', 27), ('Richie Laryea (Defensa)', 29), ('Jonathan Osorio (Mediocampista)', 32),
        ('Stephen Eustaquio (Mediocampista)', 27), ('Atiba Hutchinson (Mediocampista)', 40), ('Samuel Piette (Mediocampista)', 31),
        ('Alphonso Davies (Defensa)', 24), ('Cyle Larin (Delantero)', 29), ('Tajon Buchanan (Delantero)', 25),
        ('Jonathan David (Delantero)', 24), ('Lucas Cavallini (Delantero)', 31), ('Theo Corbeanu (Delantero)', 23),
        ('Liam Fraser (Mediocampista)', 27), ('Mark-Anthony Kaye (Mediocampista)', 29), ('Ali Ahmed (Mediocampista)', 22),
        ('Ismael Kone (Mediocampista)', 22), ('Jacob Shaffelburg (Delantero)', 24), ('David Wotherspoon (Mediocampista)', 34),
        ('Luca Koleosho (Delantero)', 20), ('Mathieu Choiniere (Delantero)', 24),
    ],
    'Bosnia Herzegovina': [
        ('Vedran Kjosevski (Portero)', 27), ('Ibrahim Sehic (Portero)', 35), ('Nermin Jasarevic (Portero)', 27),
        ('Amir Hadziahmetovic (Mediocampista)', 26), ('Anel Ahmedhodžic (Defensa)', 25), ('Ermin Bicakcic (Defensa)', 35),
        ('Sead Kolasinac (Defensa)', 31), ('Tin Jedvaj (Defensa)', 29), ('Miralem Pjanic (Mediocampista)', 34),
        ('Edin Dzeko (Delantero)', 38), ('Amer Gojak (Mediocampista)', 28), ('Rade Krunic (Mediocampista)', 30),
        ('Haris Hajradinovic (Mediocampista)', 27), ('Armin Hodžic (Delantero)', 29), ('Sasa Kalajdzic (Delantero)', 27),
        ('Ermedin Demirovic (Delantero)', 26), ('Nedim Bajric (Mediocampista)', 22), ('Luka Menalo (Delantero)', 29),
        ('Sinisa Babic (Defensa)', 27), ('Jasmin Mujezinovic (Defensa)', 26), ('Gojko Cimirot (Mediocampista)', 32),
        ('Dario Saric (Mediocampista)', 28), ('Džemal Muhic (Delantero)', 22), ('Harun Arslanagic (Defensa)', 30),
        ('Adnan Kovacevic (Defensa)', 30), ('Benjamin Tatar (Delantero)', 25),
    ],
    'Qatar': [
        ('Meshaal Barsham (Portero)', 25), ('Yousef Hassan (Portero)', 32), ('Salah Zakaria (Portero)', 27),
        ('Pedro Miguel (Defensa)', 33), ('Bassam Al-Rawi (Defensa)', 28), ('Abdelkarim Hassan (Defensa)', 30),
        ('Tarek Salman (Defensa)', 22), ('Homam Ahmed (Mediocampista)', 23), ('Hassan Al-Haydos (Mediocampista)', 32),
        ('Akram Afif (Delantero)', 27), ('Almoez Ali (Delantero)', 28), ('Assim Madibo (Mediocampista)', 26),
        ('Karim Boudiaf (Mediocampista)', 33), ('Ismaeel Mohammad (Mediocampista)', 25), ('Mohammed Muntari (Delantero)', 27),
        ('Ahmed Alaaeldin (Mediocampista)', 29), ('Jassem Gaber (Defensa)', 24), ('Yusuf Abdurisag (Delantero)', 26),
        ('Ahmed Fatehi (Defensa)', 29), ('Murad Naser (Mediocampista)', 22), ('Khalid Muneer (Delantero)', 24),
        ('Hamad Al-Amari (Defensa)', 27), ('Ali Asadalla (Mediocampista)', 26), ('Omar Khaled (Mediocampista)', 23),
        ('Ahmed Al-Rawi (Defensa)', 25), ('Naif Al-Hadhrami (Mediocampista)', 28),
    ],
    'Suiza': [
        ('Yann Sommer (Portero)', 35), ('Gregor Kobel (Portero)', 26), ('Jonas Omlin (Portero)', 30),
        ('Manuel Akanji (Defensa)', 29), ('Nico Elvedi (Defensa)', 27), ('Ricardo Rodriguez (Defensa)', 32),
        ('Silvan Widmer (Defensa)', 31), ('Fabian Schar (Defensa)', 32), ('Granit Xhaka (Mediocampista)', 32),
        ('Remo Freuler (Mediocampista)', 32), ('Denis Zakaria (Mediocampista)', 27), ('Ruben Vargas (Mediocampista)', 26),
        ('Xherdan Shaqiri (Delantero)', 32), ('Breel Embolo (Delantero)', 27), ('Haris Seferovic (Delantero)', 31),
        ('Noah Okafor (Delantero)', 24), ('Zeki Amdouni (Delantero)', 24), ('Michel Aebischer (Mediocampista)', 27),
        ('Christian Fassnacht (Delantero)', 30), ('Cedric Zesiger (Defensa)', 26), ('Ulisses Garcia (Defensa)', 28),
        ('Dan Ndoye (Delantero)', 24), ('Ardon Jashari (Mediocampista)', 22), ('Vincent Sierro (Mediocampista)', 29),
        ('Filip Ugrinic (Mediocampista)', 25), ('Kwadwo Duah (Delantero)', 27),
    ],
    'Brasil': [
        ('Alisson Becker (Portero)', 32), ('Ederson Moraes (Portero)', 31), ('Bento Krepski (Portero)', 24),
        ('Marquinhos (Defensa)', 30), ('Eder Militao (Defensa)', 26), ('Gabriel Magalhaes (Defensa)', 26),
        ('Danilo Luiz (Defensa)', 33), ('Alex Telles (Defensa)', 31), ('Casemiro (Mediocampista)', 32),
        ('Fabinho (Mediocampista)', 30), ('Bruno Guimaraes (Mediocampista)', 26), ('Lucas Paqueta (Mediocampista)', 26),
        ('Neymar Jr. (Delantero)', 34), ('Vinicius Jr. (Delantero)', 24), ('Rodrygo Goes (Delantero)', 23),
        ('Richarlison (Delantero)', 27), ('Rafael Leao (Delantero)', 25), ('Endrick Felipe (Delantero)', 18),
        ('Savinho (Delantero)', 20), ('Andreas Pereira (Mediocampista)', 28), ('Alex Grimaldo (Defensa)', 29),
        ('Yan Couto (Defensa)', 22), ('Gerson (Mediocampista)', 27), ('Guilherme Arana (Defensa)', 27),
        ('Wendell (Defensa)', 30), ('Matheus Cunha (Delantero)', 25),
    ],
    'Marruecos': [
        ('Yassine Bounou (Portero)', 33), ('Ahmed Reda Tagnaouti (Portero)', 28), ('Munir El Kajoui (Portero)', 30),
        ('Achraf Hakimi (Defensa)', 25), ('Romain Saiss (Defensa)', 34), ('Nayef Aguerd (Defensa)', 27),
        ('Jawad El Yamiq (Defensa)', 31), ('Noussair Mazraoui (Defensa)', 26), ('Azzedine Ounahi (Mediocampista)', 24),
        ('Sofyan Amrabat (Mediocampista)', 27), ('Selim Amallah (Mediocampista)', 27), ('Hakim Ziyech (Delantero)', 32),
        ('Youssef En-Nesyri (Delantero)', 27), ('Sofiane Boufal (Delantero)', 30), ('Abdelhamid Sabiri (Mediocampista)', 27),
        ('Ilias Chair (Mediocampista)', 26), ('Tarik Tissoudali (Delantero)', 30), ('Anass Zaroury (Delantero)', 24),
        ('Ibrahim Salah (Delantero)', 23), ('Yahia Attiat-Allah (Defensa)', 29), ('Hamza Mendyl (Defensa)', 27),
        ('Badr Benoun (Defensa)', 31), ('Zakaria Aboukhlal (Delantero)', 23), ('Mohamed Chibi (Mediocampista)', 22),
        ('Ryan Mmaee (Delantero)', 27), ('Bilal El Khannouss (Mediocampista)', 20),
    ],
    'Haiti': [
        ('Josue Duverger (Portero)', 28), ('Jonathan Constante (Portero)', 26), ('Donalson Senecharles (Portero)', 24),
        ('Andrew Desire (Defensa)', 27), ('Mechack Jerome (Defensa)', 29), ('Steeven Saba (Defensa)', 26),
        ('Carlo Namphy (Defensa)', 28), ('Michael Perez (Defensa)', 25), ('Frantzdy Pierrot (Mediocampista)', 25),
        ('Derrick Etienne Jr (Delantero)', 28), ('Kervens Belfort (Delantero)', 33), ('Wilde-Donald Guerrier (Delantero)', 33),
        ('Duckens Nazon (Delantero)', 31), ('Frederic Evens Luboya (Mediocampista)', 26), ('Reginal Goreux (Defensa)', 36),
        ('Khaly Thiam (Mediocampista)', 27), ('Pascal Comvalius (Delantero)', 35), ('Jeff Louis (Mediocampista)', 27),
        ('Herve Bazile (Mediocampista)', 30), ('Schneider Dorvil (Mediocampista)', 25), ('Marc-Antoine Fortune (Delantero)', 24),
        ('Zachary Brault-Guillard (Defensa)', 27), ('Kenny Lala (Defensa)', 32), ('Naomie Ngoy (Mediocampista)', 24),
        ('Josue Duperval (Delantero)', 23), ('Jean-Michel Alexandre (Mediocampista)', 22),
    ],
    'Escocia': [
        ('Angus Gunn (Portero)', 28), ('Craig Gordon (Portero)', 41), ('Liam Kelly (Portero)', 30),
        ('Andy Robertson (Defensa)', 31), ('Grant Hanley (Defensa)', 32), ('Scott McKenna (Defensa)', 30),
        ('Kieran Tierney (Defensa)', 27), ('Anthony Ralston (Defensa)', 25), ('Callum McGregor (Mediocampista)', 30),
        ('Stuart Armstrong (Mediocampista)', 32), ('Ryan Christie (Mediocampista)', 29), ('Billy Gilmour (Mediocampista)', 23),
        ('Scott McTominay (Mediocampista)', 27), ('Che Adams (Delantero)', 28), ('Lyndon Dykes (Delantero)', 29),
        ('Lawrence Shankland (Delantero)', 29), ('Ryan Porteous (Defensa)', 25), ('Aaron Hickey (Defensa)', 22),
        ('Ben Doak (Delantero)', 19), ('Ross McCrorie (Mediocampista)', 27), ('Kenny McLean (Mediocampista)', 32),
        ('Liam Cooper (Defensa)', 33), ('Greg Taylor (Defensa)', 26), ('John McGinn (Mediocampista)', 29),
        ('Kevin Nisbet (Delantero)', 27), ('Josh Doig (Defensa)', 22),
    ],
    'Estados Unidos': [
        ('Matt Turner (Portero)', 30), ('Zack Steffen (Portero)', 31), ('Patrick Schulte (Portero)', 23),
        ('Sergino Dest (Defensa)', 24), ('DeAndre Yedlin (Defensa)', 32), ('Walker Zimmerman (Defensa)', 31),
        ('Miles Robinson (Defensa)', 28), ('Antonee Robinson (Defensa)', 27), ('Tyler Adams (Mediocampista)', 25),
        ('Weston McKennie (Mediocampista)', 26), ('Yunus Musah (Mediocampista)', 22), ('Christian Pulisic (Delantero)', 26),
        ('Gio Reyna (Mediocampista)', 22), ('Josh Sargent (Delantero)', 24), ('Ricardo Pepi (Delantero)', 22),
        ('Folarin Balogun (Delantero)', 23), ('Tim Weah (Delantero)', 24), ('Brenden Aaronson (Mediocampista)', 24),
        ('Luca de la Torre (Mediocampista)', 26), ('Joe Scally (Defensa)', 22), ('Malik Tillman (Mediocampista)', 23),
        ('Chris Richards (Defensa)', 24), ('Cameron Carter-Vickers (Defensa)', 26), ('Caleb Wiley (Defensa)', 19),
        ('Patrick Agyemang (Delantero)', 22), ('Cade Cowell (Delantero)', 21),
    ],
    'Paraguay': [
        ('Antony Silva (Portero)', 38), ('Alfredo Aguilar (Portero)', 30), ('Alex Villagra (Portero)', 27),
        ('Gustavo Gomez (Defensa)', 31), ('Junior Alonso (Defensa)', 29), ('Santiago Arzamendia (Defensa)', 26),
        ('Omar Alderete (Defensa)', 28), ('Robert Rojas (Defensa)', 27), ('Andres Cubas (Mediocampista)', 27),
        ('Miguel Almiron (Mediocampista)', 30), ('Matias Rojas (Mediocampista)', 28), ('Angel Romero (Delantero)', 31),
        ('Oscar Romero (Mediocampista)', 31), ('Antonio Sanabria (Delantero)', 28), ('Alex Arce (Delantero)', 28),
        ('Ivan Ramirez (Delantero)', 25), ('Julio Enciso (Delantero)', 20), ('Gabriel Avalos (Delantero)', 29),
        ('Juan Espinoza (Defensa)', 25), ('Richard Ortiz (Mediocampista)', 34), ('Braian Ojeda (Mediocampista)', 24),
        ('Damian Bobadilla (Mediocampista)', 26), ('Alberto Espinola (Mediocampista)', 24), ('Nicolas Gamarra (Defensa)', 26),
        ('Carlos Gonzalez (Delantero)', 31), ('Diego Gomez (Mediocampista)', 23),
    ],
    'Australia': [
        ('Mat Ryan (Portero)', 32), ('Danny Vukovic (Portero)', 37), ('Joe Gauci (Portero)', 25),
        ('Harry Souttar (Defensa)', 25), ('Milos Degenek (Defensa)', 33), ('Aziz Behich (Defensa)', 34),
        ('Nathaniel Atkinson (Defensa)', 24), ('Bailey Wright (Defensa)', 32), ('Jackson Irvine (Mediocampista)', 31),
        ('Aaron Mooy (Mediocampista)', 34), ('Riley McGree (Mediocampista)', 26), ('Ryan Strain (Defensa)', 27),
        ('Mathew Leckie (Delantero)', 33), ('Mitchell Duke (Delantero)', 33), ('Martin Boyle (Delantero)', 31),
        ('Jamie Maclaren (Delantero)', 31), ('Craig Goodwin (Delantero)', 32), ('Cameron Devlin (Mediocampista)', 26),
        ('Ajdin Hrustic (Mediocampista)', 27), ('Kusini Yengi (Delantero)', 24), ('Jordan Bos (Defensa)', 25),
        ('Nestory Irankunda (Delantero)', 19), ('Lachie Wales (Mediocampista)', 24), ('Brandon Borrello (Delantero)', 30),
        ('Garang Kuol (Delantero)', 20), ('Reno Piscopo (Mediocampista)', 25),
    ],
    'Turquia': [
        ('Ugurcan Cakir (Portero)', 27), ('Altay Bayindir (Portero)', 26), ('Mert Gunok (Portero)', 35),
        ('Merih Demiral (Defensa)', 26), ('Abdulkerim Bardakci (Defensa)', 26), ('Samet Akaydin (Defensa)', 27),
        ('Zeki Celik (Defensa)', 27), ('Ferdi Kadioglu (Defensa)', 24), ('Hakan Calhanoglu (Mediocampista)', 30),
        ('Salih Ozcan (Mediocampista)', 26), ('Orkun Kokcu (Mediocampista)', 24), ('Arda Guler (Mediocampista)', 20),
        ('Kerem Akturkoglu (Delantero)', 25), ('Cenk Tosun (Delantero)', 33), ('Burak Yilmaz (Delantero)', 39),
        ('Baris Alper Yilmaz (Delantero)', 23), ('Bertug Yildirim (Delantero)', 23), ('Yusuf Yazici (Mediocampista)', 27),
        ('Ismail Yuksek (Mediocampista)', 25), ('Okay Yokuslu (Mediocampista)', 30), ('Caglar Soyuncu (Defensa)', 28),
        ('Mert Muldur (Defensa)', 25), ('Umut Nayir (Delantero)', 28), ('Ogulcan Ugur (Defensa)', 27),
        ('Halil Dervisoglu (Delantero)', 24), ('Can Uzun (Delantero)', 20),
    ],
    'Alemania': [
        ('Manuel Neuer (Portero)', 39), ('Marc-Andre ter Stegen (Portero)', 33), ('Oliver Baumann (Portero)', 34),
        ('Antonio Rudiger (Defensa)', 31), ('Nico Schlotterbeck (Defensa)', 25), ('David Raum (Defensa)', 26),
        ('Jonathan Tah (Defensa)', 28), ('Thilo Kehrer (Defensa)', 27), ('Joshua Kimmich (Mediocampista)', 29),
        ('Leon Goretzka (Mediocampista)', 29), ('Ilkay Gundogan (Mediocampista)', 34), ('Florian Wirtz (Mediocampista)', 22),
        ('Kai Havertz (Mediocampista)', 26), ('Thomas Muller (Delantero)', 35), ('Jamal Musiala (Mediocampista)', 22),
        ('Leroy Sane (Delantero)', 29), ('Serge Gnabry (Delantero)', 29), ('Niclas Fullkrug (Delantero)', 32),
        ('Timo Werner (Delantero)', 29), ('Benjamin Henrichs (Defensa)', 29), ('Robin Gosens (Defensa)', 30),
        ('Mattias Ginter (Defensa)', 30), ('Pascal Gross (Mediocampista)', 33), ('Emre Can (Mediocampista)', 30),
        ('Chris Fuhrich (Delantero)', 26), ('Tim Kleindienst (Delantero)', 28),
    ],
    'Curazao': [
        ('Eloy Room (Portero)', 33), ('Wuilker Farinez (Portero)', 27), ('Ruben Verhoeven (Portero)', 29),
        ('Cuco Martina (Defensa)', 36), ('Jurien Gaari (Defensa)', 29), ('Leandro Bacuna (Mediocampista)', 33),
        ('Charlison Benschop (Delantero)', 34), ('Jarchinio Antonia (Delantero)', 31), ('Genevieve Doelwijt (Mediocampista)', 27),
        ('Rangelo Janga (Delantero)', 31), ('Gideon van Zwam (Portero)', 31), ('Ethan Flemming (Delantero)', 23),
        ('Quentin Boisgard (Mediocampista)', 24), ('Kenji Gorre (Mediocampista)', 29), ('Cedric van der Gun (Defensa)', 27),
        ('Ryan Emanuelson (Defensa)', 35), ('Elson Hooi (Mediocampista)', 29), ('Gevero Markiet (Defensa)', 26),
        ('Daniel Lareynie (Mediocampista)', 25), ('Myron Boadu (Delantero)', 23), ('Carel Eiting (Mediocampista)', 26),
        ('Jurgen Ekkelenkamp (Mediocampista)', 24), ('Daishawn Redan (Delantero)', 24), ('Ryan Donk (Defensa)', 36),
        ('Godfried Roemeratoe (Defensa)', 24), ('Jamiro Monteiro (Mediocampista)', 30),
    ],
    'Costa de Marfil': [
        ('Yahia Fofana (Portero)', 30), ('Badra Ali Sangare (Portero)', 35), ('Brice Dja Djedje (Portero)', 29),
        ('Simon Deli (Defensa)', 33), ('Serge Aurier (Defensa)', 31), ('Ghislain Konan (Defensa)', 28),
        ('Odilon Kossounou (Defensa)', 23), ('Willy Boly (Defensa)', 33), ('Franck Kessie (Mediocampista)', 27),
        ('Seko Fofana (Mediocampista)', 29), ('Ibrahim Sangare (Mediocampista)', 26), ('Jean-Michael Seri (Mediocampista)', 32),
        ('Nicolas Pepe (Delantero)', 29), ('Wilfried Zaha (Delantero)', 32), ('Sebastien Haller (Delantero)', 30),
        ('Jonathan Bamba (Delantero)', 28), ('Maxwell Cornet (Delantero)', 28), ('Amad Diallo (Delantero)', 22),
        ('Simon Adingra (Delantero)', 22), ('Silas (Delantero)', 24), ('Jeremie Boga (Delantero)', 27),
        ('Eric Bailly (Defensa)', 30), ('Cheick Doukoure (Mediocampista)', 23), ('Karim Diakite (Defensa)', 24),
        ('Oumar Diakite (Mediocampista)', 25), ('Christian Kouame (Delantero)', 26),
    ],
    'Ecuador': [
        ('Hernan Galindez (Portero)', 35), ('Alexander Dominguez (Portero)', 38), ('Wellington Ramirez (Portero)', 27),
        ('Piero Hincapie (Defensa)', 22), ('Felix Torres (Defensa)', 27), ('Angelo Preciado (Defensa)', 26),
        ('Diego Palacios (Defensa)', 26), ('Robert Arboleda (Defensa)', 31), ('Carlos Gruezo (Mediocampista)', 29),
        ('Moises Caicedo (Mediocampista)', 23), ('Jose Cifuentes (Mediocampista)', 25), ('Gonzalo Plata (Delantero)', 23),
        ('Jeremy Sarmiento (Mediocampista)', 22), ('Romario Ibarra (Delantero)', 30), ('Enner Valencia (Delantero)', 34),
        ('Kevin Rodriguez (Delantero)', 22), ('Leonardo Campana (Delantero)', 23), ('Djorkaeff Reasco (Delantero)', 24),
        ('Kenny Contreras (Mediocampista)', 24), ('Sergio Quintero (Delantero)', 25), ('William Palacios (Mediocampista)', 23),
        ('Ivan Angulo (Delantero)', 26), ('Jorge Preciado (Delantero)', 22), ('Pervis Estupinan (Defensa)', 26),
        ('Alan Minda (Mediocampista)', 24), ('Xavier Arreaga (Defensa)', 30),
    ],
    'Holanda': [
        ('Remko Pasveer (Portero)', 40), ('Mark Flekken (Portero)', 31), ('Bart Verbruggen (Portero)', 22),
        ('Virgil van Dijk (Defensa)', 34), ('Matthijs de Ligt (Defensa)', 25), ('Denzel Dumfries (Defensa)', 28),
        ('Daley Blind (Defensa)', 34), ('Nathan Ake (Defensa)', 30), ('Frenkie de Jong (Mediocampista)', 27),
        ('Ryan Gravenberch (Mediocampista)', 22), ('Teun Koopmeiners (Mediocampista)', 26), ('Xavi Simons (Mediocampista)', 22),
        ('Memphis Depay (Delantero)', 30), ('Cody Gakpo (Delantero)', 25), ('Steven Bergwijn (Delantero)', 26),
        ('Donyell Malen (Delantero)', 26), ('Wout Weghorst (Delantero)', 32), ('Tijjani Reijnders (Mediocampista)', 26),
        ('Jeremie Frimpong (Defensa)', 24), ('Brian Brobbey (Delantero)', 23), ('Lutsharel Geertruida (Defensa)', 24),
        ('Jurrien Timber (Defensa)', 23), ('Quinten Timber (Mediocampista)', 23), ('Micky van de Ven (Defensa)', 23),
        ('Joshua Zirkzee (Delantero)', 23), ('Ian Maatsen (Defensa)', 22),
    ],
    'Japon': [
        ('Shuichi Gonda (Portero)', 34), ('Zion Suzuki (Portero)', 22), ('Keisuke Osako (Portero)', 28),
        ('Takehiro Tomiyasu (Defensa)', 26), ('Ko Itakura (Defensa)', 27), ('Hiroki Ito (Defensa)', 24),
        ('Yuto Nagatomo (Defensa)', 38), ('Miki Yamane (Defensa)', 29), ('Wataru Endo (Mediocampista)', 31),
        ('Gaku Shibasaki (Mediocampista)', 32), ('Hidemasa Morita (Mediocampista)', 29), ('Kaoru Mitoma (Delantero)', 27),
        ('Junya Ito (Delantero)', 31), ('Takumi Minamino (Mediocampista)', 29), ('Daizen Maeda (Delantero)', 27),
        ('Ritsu Doan (Mediocampista)', 26), ('Ayase Ueda (Delantero)', 26), ('Takefusa Kubo (Mediocampista)', 23),
        ('Ao Tanaka (Mediocampista)', 26), ('Shogo Taniguchi (Defensa)', 32), ('Yukinari Sugawara (Defensa)', 22),
        ('Reo Hatate (Mediocampista)', 27), ('Koki Machida (Defensa)', 27), ('Yuki Soma (Mediocampista)', 27),
        ('Keito Nakamura (Delantero)', 23), ('Ayumu Seko (Mediocampista)', 22),
    ],
    'Suecia': [
        ('Robin Olsen (Portero)', 34), ('Karl-Johan Johnsson (Portero)', 35), ('Andreas Linde (Portero)', 31),
        ('Victor Lindelof (Defensa)', 30), ('Mikael Lustig (Defensa)', 37), ('Emil Krafth (Defensa)', 30),
        ('Filip Helander (Defensa)', 32), ('Ludwig Augustinsson (Defensa)', 30), ('Sebastian Larsson (Mediocampista)', 39),
        ('Albin Ekdal (Mediocampista)', 35), ('Mattias Svanberg (Mediocampista)', 26), ('Samuel Gustafson (Mediocampista)', 31),
        ('Viktor Claesson (Mediocampista)', 32), ('Alexander Isak (Delantero)', 26), ('Dejan Kulusevski (Mediocampista)', 24),
        ('Anthony Elanga (Delantero)', 22), ('Zlatan Ibrahimovic (Delantero)', 44), ('Robin Quaison (Delantero)', 31),
        ('Jesper Karlsson (Delantero)', 26), ('Pontus Jansson (Defensa)', 33), ('Marcus Danielson (Defensa)', 33),
        ('Jordan Larsson (Delantero)', 27), ('Isak Hien (Defensa)', 23), ('Lucas Bergvall (Mediocampista)', 18),
        ('Svante Ingelsson (Mediocampista)', 22), ('Patrik Walemark (Delantero)', 24),
    ],
    'Tunez': [
        ('Aymen Dahmen (Portero)', 27), ('Bechir Ben Said (Portero)', 36), ('Mouez Hassen (Portero)', 29),
        ('Montassar Talbi (Defensa)', 25), ('Wajdi Kechrida (Defensa)', 30), ('Dylan Bronn (Defensa)', 28),
        ('Ali Maaloul (Defensa)', 34), ('Yassine Meriah (Defensa)', 30), ('Ellyes Skhiri (Mediocampista)', 28),
        ('Aissa Laidouni (Mediocampista)', 27), ('Mohamed Ali Ben Romdhane (Mediocampista)', 26), ('Hannibal Mejbri (Mediocampista)', 21),
        ('Wahbi Khazri (Delantero)', 33), ('Naim Sliti (Delantero)', 32), ('Issam Jebali (Delantero)', 30),
        ('Youssef Msakni (Delantero)', 34), ('Seifeddine Jaziri (Delantero)', 28), ('Mohamed Drager (Defensa)', 27),
        ('Hamza Rafia (Mediocampista)', 24), ('Ghailene Chaalali (Mediocampista)', 29), ('Taha Khenissi (Delantero)', 34),
        ('Ferjani Sassi (Mediocampista)', 32), ('Nizar Issaoui (Defensa)', 27), ('Mohamed Ben Hmida (Mediocampista)', 23),
        ('Mortadha Ben Ouanes (Delantero)', 25), ('Karim Laaribi (Mediocampista)', 26),
    ],
    'Belgica': [
        ('Thibaut Courtois (Portero)', 32), ('Simon Mignolet (Portero)', 36), ('Koen Casteels (Portero)', 32),
        ('Toby Alderweireld (Defensa)', 35), ('Jan Vertonghen (Defensa)', 37), ('Thomas Meunier (Defensa)', 32),
        ('Axel Witsel (Mediocampista)', 35), ('Kevin De Bruyne (Mediocampista)', 33), ('Youri Tielemans (Mediocampista)', 27),
        ('Amadou Onana (Mediocampista)', 23), ('Dodi Lukebakio (Delantero)', 27), ('Jeremy Doku (Delantero)', 22),
        ('Romelu Lukaku (Delantero)', 31), ('Leandro Trossard (Delantero)', 29), ('Lois Openda (Delantero)', 24),
        ('Johan Bakayoko (Delantero)', 21), ('Wout Faes (Defensa)', 26), ('Arthur Theate (Defensa)', 24),
        ('Zeno Debast (Defensa)', 21), ('Orel Mangala (Mediocampista)', 26), ('Charles De Ketelaere (Mediocampista)', 23),
        ('Aster Vranckx (Mediocampista)', 22), ('Rasmus Kristensen (Defensa)', 27), ('Thomas Kaminski (Portero)', 32),
        ('Hugo Cuypers (Delantero)', 27), ('Alexis Mac Allister (Mediocampista)', 25),
    ],
    'Egipto': [
        ('Mohamed El-Shenawy (Portero)', 36), ('Mohamed Abou Gabal (Portero)', 33), ('Ahmed El-Shenawy (Portero)', 28),
        ('Ahmed Hegazy (Defensa)', 33), ('Mohamed Abdel-Moneim (Defensa)', 30), ('Karim Hafez (Defensa)', 28),
        ('Akram Tawfik (Defensa)', 24), ('Omar Gaber (Defensa)', 31), ('Tarek Hamed (Mediocampista)', 35),
        ('Hamdi Fathi (Mediocampista)', 28), ('Ahmed Sayed Zizo (Mediocampista)', 29), ('Amr El-Sulaya (Mediocampista)', 26),
        ('Mohamed Salah (Delantero)', 34), ('Mostafa Mohamed (Delantero)', 26), ('Trezeguet (Delantero)', 29),
        ('Ramadan Sobhi (Delantero)', 27), ('Marwan Hamdy (Delantero)', 25), ('Ahmed Hamed (Mediocampista)', 26),
        ('Emam Ashour (Mediocampista)', 28), ('Mahmoud Alaa (Portero)', 28), ('Wessam Abou Ali (Delantero)', 26),
        ('Omar Marmoush (Delantero)', 26), ('Ibrahim Adel (Delantero)', 22), ('Zaki Attia (Mediocampista)', 24),
        ('Nasser Maher (Mediocampista)', 26), ('Fathy Ali (Defensa)', 25),
    ],
    'Iran': [
        ('Alireza Beiranvand (Portero)', 32), ('Hossein Hosseini (Portero)', 30), ('Payam Niazmand (Portero)', 30),
        ('Majid Hosseini (Defensa)', 27), ('Shoja Khalilzadeh (Defensa)', 34), ('Ehsan Hajsafi (Defensa)', 34),
        ('Abolfazl Jalali (Defensa)', 25), ('Milad Mohammadi (Defensa)', 30), ('Saeid Ezatolahi (Mediocampista)', 28),
        ('Ali Gholizadeh (Mediocampista)', 28), ('Ahmad Noorollahi (Mediocampista)', 30), ('Saman Ghoddos (Mediocampista)', 30),
        ('Mehdi Taremi (Delantero)', 32), ('Sardar Azmoun (Delantero)', 30), ('Allahyar Sayyad (Delantero)', 24),
        ('Karim Ansarifard (Delantero)', 35), ('Alireza Jahanbakhsh (Delantero)', 31), ('Morteza Pouraliganji (Defensa)', 32),
        ('Morteza Rezaeian (Defensa)', 28), ('Omid Noorafkan (Mediocampista)', 28), ('Ramin Rezaeian (Defensa)', 33),
        ('Mehdi Ghayedi (Mediocampista)', 25), ('Shahin Taheri (Delantero)', 22), ('Farshad Ahmadzadeh (Mediocampista)', 26),
        ('Moein Hosseini (Defensa)', 24), ('Amir Arsalan Motahhari (Mediocampista)', 27),
    ],
    'Nueva Zelanda': [
        ('Oliver Sail (Portero)', 28), ('Stefan Marinovic (Portero)', 34), ('Michael Woud (Portero)', 28),
        ('Winston Reid (Defensa)', 36), ('Tommy Smith (Defensa)', 36), ('Tim Payne (Defensa)', 31),
        ('Michael Boxall (Defensa)', 35), ('Liberato Cacace (Defensa)', 24), ('Noah Billingsley (Defensa)', 22),
        ('Clayton Lewis (Mediocampista)', 27), ('Ryan Thomas (Mediocampista)', 31), ('Marko Stamenic (Mediocampista)', 23),
        ('Joe Bell (Mediocampista)', 25), ('Marco Rojas (Delantero)', 33), ('Chris Wood (Delantero)', 32),
        ('Matthew Garbett (Mediocampista)', 24), ('Elijah Just (Mediocampista)', 23), ('Logan Rogerson (Delantero)', 23),
        ('Ben Waine (Delantero)', 24), ('Darryl Lachman (Defensa)', 33), ('Alex Rufer (Mediocampista)', 28),
        ('Myer Bevan (Delantero)', 22), ('Callum McCowatt (Delantero)', 27), ('Declan Edge (Mediocampista)', 23),
        ('Zac Hansell (Mediocampista)', 22), ('Kosta Barbarouses (Delantero)', 35),
    ],
    'Espana': [
        ('Unai Simon (Portero)', 27), ('David Raya (Portero)', 29), ('Robert Sanchez (Portero)', 26),
        ('Dani Carvajal (Defensa)', 32), ('Aymeric Laporte (Defensa)', 30), ('Pau Torres (Defensa)', 27),
        ('Alejandro Balde (Defensa)', 21), ('Robin Le Normand (Defensa)', 27), ('Rodri (Mediocampista)', 28),
        ('Pedri (Mediocampista)', 22), ('Gavi (Mediocampista)', 20), ('Fabian Ruiz (Mediocampista)', 27),
        ('Ferran Torres (Delantero)', 24), ('Dani Olmo (Mediocampista)', 26), ('Alvaro Morata (Delantero)', 31),
        ('Joselu (Delantero)', 34), ('Lamine Yamal (Delantero)', 18), ('Nico Williams (Delantero)', 22),
        ('Mikel Merino (Mediocampista)', 28), ('Nacho Fernandez (Defensa)', 34), ('Marc Cucurella (Defensa)', 25),
        ('Cesar Azpilicueta (Defensa)', 35), ('Bryan Zaragoza (Delantero)', 23), ('Mikel Oyarzabal (Delantero)', 27),
        ('Alex Baena (Mediocampista)', 23), ('Yeremy Pino (Delantero)', 22),
    ],
    'Cabo Verde': [
        ('Vozinha (Portero)', 33), ('Ricardo Moreira (Portero)', 28), ('Marcio Rosa (Portero)', 27),
        ('Roberto Lopes (Defensa)', 30), ('Diney (Defensa)', 27), ('Stopira (Defensa)', 36),
        ('Efigenio Mendes (Defensa)', 26), ('Kenny Rocha (Mediocampista)', 28), ('Lisandro Semedo (Mediocampista)', 30),
        ('Ryan Mendes (Delantero)', 35), ('Garry Rodrigues (Delantero)', 32), ('Djaniny (Delantero)', 31),
        ('Steven Fortes (Defensa)', 32), ('Jamiro Monteiro (Mediocampista)', 30), ('Patrick Andrade (Mediocampista)', 29),
        ('Julio Tavares (Delantero)', 35), ('Bryan Teixeira (Delantero)', 23), ('Joao Pedro Costa (Mediocampista)', 25),
        ('Kevin Pina (Mediocampista)', 24), ('Vagner Dias (Mediocampista)', 27), ('Heldon Ramos (Delantero)', 34),
        ('Nuno Borges (Defensa)', 26), ('Pedrinho (Delantero)', 24), ('Fabio Fortes (Delantero)', 28),
        ('Kika Fati (Mediocampista)', 22), ('Joel Monteiro (Defensa)', 26),
    ],
    'Arabia Saudita': [
        ('Mohammed Al-Owais (Portero)', 32), ('Fawaz Al-Qarni (Portero)', 29), ('Nawaf Al-Aqidi (Portero)', 25),
        ('Ali Al-Bulayhi (Defensa)', 34), ('Abdulelah Al-Amri (Defensa)', 26), ('Saud Abdulhamid (Defensa)', 24),
        ('Hassan Tambakti (Defensa)', 23), ('Ali Al-Hassan (Defensa)', 28), ('Salman Al-Faraj (Mediocampista)', 34),
        ('Mohamed Kanno (Mediocampista)', 26), ('Ali Al-Nimer (Mediocampista)', 25), ('Sami Al-Najei (Mediocampista)', 30),
        ('Salem Al-Dawsari (Delantero)', 32), ('Firas Al-Buraikan (Delantero)', 24), ('Abdullah Al-Hamdan (Delantero)', 23),
        ('Hattan Bahebri (Delantero)', 28), ('Nasser Al-Dawsari (Delantero)', 27), ('Fahad Al-Muwallad (Delantero)', 30),
        ('Mohammed Al-Burayk (Defensa)', 31), ('Riyadh Sharahili (Mediocampista)', 26), ('Yasser Al-Shahrani (Defensa)', 31),
        ('Nawaf Al-Abid (Mediocampista)', 24), ('Sultan Al-Ghanam (Delantero)', 25), ('Taiseer Al-Jassim (Mediocampista)', 29),
        ('Ibrahim Al-Kharashi (Defensa)', 27), ('Nayef Aguerd (Delantero)', 24),
    ],
    'Uruguay': [
        ('Fernando Muslera (Portero)', 38), ('Sebastian Sosa (Portero)', 36), ('Sergio Rochet (Portero)', 30),
        ('Diego Godin (Defensa)', 38), ('Jose Maria Gimenez (Defensa)', 30), ('Ronald Araujo (Defensa)', 25),
        ('Mathias Olivera (Defensa)', 27), ('Martin Caceres (Defensa)', 37), ('Rodrigo Bentancur (Mediocampista)', 27),
        ('Federico Valverde (Mediocampista)', 26), ('Matias Vecino (Mediocampista)', 33), ('Manuel Ugarte (Mediocampista)', 23),
        ('Luis Suarez (Delantero)', 38), ('Edinson Cavani (Delantero)', 37), ('Darwin Nunez (Delantero)', 25),
        ('Facundo Torres (Delantero)', 24), ('Maximo Perrone (Mediocampista)', 21), ('Brian Ocampo (Delantero)', 23),
        ('Agustin Canobbio (Delantero)', 25), ('Nahitan Nandez (Mediocampista)', 29), ('Santiago Bueno (Defensa)', 26),
        ('Nicolas De La Cruz (Mediocampista)', 27), ('Facundo Pellistri (Delantero)', 23), ('Sebastian Cabildo (Defensa)', 24),
        ('Luciano Rodriguez (Delantero)', 21), ('Marcelo Saracchi (Defensa)', 27),
    ],
    'Francia': [
        ('Mike Maignan (Portero)', 29), ('Alphonse Areola (Portero)', 31), ('Brice Samba (Portero)', 30),
        ('William Saliba (Defensa)', 23), ('Dayot Upamecano (Defensa)', 26), ('Benjamin Pavard (Defensa)', 28),
        ('Theo Hernandez (Defensa)', 27), ('Jules Kounde (Defensa)', 26), ('N\'Golo Kante (Mediocampista)', 33),
        ('Aurelien Tchouameni (Mediocampista)', 24), ('Adrien Rabiot (Mediocampista)', 29), ('Antoine Griezmann (Delantero)', 33),
        ('Kylian Mbappe (Delantero)', 27), ('Ousmane Dembele (Delantero)', 27), ('Marcus Thuram (Delantero)', 27),
        ('Christopher Nkunku (Delantero)', 27), ('Randal Kolo Muani (Delantero)', 26), ('Matteo Guendouzi (Mediocampista)', 26),
        ('Eduardo Camavinga (Mediocampista)', 22), ('Axel Disasi (Defensa)', 27), ('Jonathan Clauss (Defensa)', 32),
        ('Ibrahima Konate (Defensa)', 25), ('Warren Zaire-Emery (Mediocampista)', 18), ('Youssouf Fofana (Mediocampista)', 25),
        ('Bradley Barcola (Delantero)', 22), ('Desire Doue (Mediocampista)', 19),
    ],
    'Senegal': [
        ('Edouard Mendy (Portero)', 32), ('Alfred Gomis (Portero)', 30), ('Seny Dieng (Portero)', 29),
        ('Kalidou Koulibaly (Defensa)', 33), ('Abdou Diallo (Defensa)', 28), ('Youssouf Sabaly (Defensa)', 32),
        ('Formose Mendy (Defensa)', 26), ('Pape Abou Cisse (Defensa)', 29), ('Cheikhou Kouyate (Mediocampista)', 34),
        ('Idrissa Gueye (Mediocampista)', 35), ('Nampalys Mendy (Mediocampista)', 32), ('Pape Matar Sarr (Mediocampista)', 22),
        ('Sadio Mane (Delantero)', 32), ('Ismaila Sarr (Delantero)', 27), ('Boulaye Dia (Delantero)', 27),
        ('Nicolas Jackson (Delantero)', 23), ('Habib Diallo (Delantero)', 29), ('Lamine Camara (Mediocampista)', 21),
        ('Iliman Ndiaye (Delantero)', 24), ('Moussa Ndiaye (Defensa)', 22), ('Krepin Diatta (Delantero)', 25),
        ('Mamadou Loum (Mediocampista)', 28), ('Pathé Ciss (Mediocampista)', 31), ('Abdallah Sima (Delantero)', 23),
        ('Pape Gueye (Mediocampista)', 25), ('El Hadji Malick Diouf (Delantero)', 22),
    ],
    'Irak': [
        ('Jalal Hassan (Portero)', 33), ('Fahad Talib (Portero)', 27), ('Mohammed Hameed (Portero)', 25),
        ('Safa Hachim (Defensa)', 31), ('Hussein Ali (Defensa)', 28), ('Ahmed Ibrahim (Defensa)', 26),
        ('Ali Adnan (Defensa)', 31), ('Rebin Sulaka (Defensa)', 27), ('Amjed Attwan (Mediocampista)', 29),
        ('Bashar Resan (Mediocampista)', 25), ('Safaa Hadi (Mediocampista)', 30), ('Mohammed Karrar (Mediocampista)', 24),
        ('Ayman Hussein (Delantero)', 27), ('Mohanad Ali (Delantero)', 29), ('Amir Al-Ammari (Delantero)', 26),
        ('Ibrahim Bayesh (Delantero)', 28), ('Justin Meram (Mediocampista)', 37), ('Ali Faez (Mediocampista)', 24),
        ('Humam Tariq (Delantero)', 23), ('Osama Rashid (Mediocampista)', 29), ('Yaser Kasim (Mediocampista)', 33),
        ('Alaa Abbas (Defensa)', 28), ('George Malki (Mediocampista)', 27), ('Ali Hassan (Defensa)', 26),
        ('Murtadha Mahdi (Delantero)', 24), ('Emad Mohammed (Delantero)', 30),
    ],
    'Noruega': [
        ('Orjan Nyland (Portero)', 34), ('Jorgen Strand Larsen (Portero)', 25), ('Sten Grytebust (Portero)', 34),
        ('Leo Ostigard (Defensa)', 25), ('Andreas Hanche-Olsen (Defensa)', 27), ('Omar Elabdellaoui (Defensa)', 32),
        ('Kristian Thorstvedt (Mediocampista)', 25), ('Fredrik Aursnes (Mediocampista)', 28), ('Martin Odegaard (Mediocampista)', 26),
        ('Sander Berge (Mediocampista)', 27), ('Mats Moller Daehli (Mediocampista)', 29), ('Erling Haaland (Delantero)', 26),
        ('Alexander Sorloth (Delantero)', 29), ('Mohamed Elyounoussi (Delantero)', 30), ('Antonio Nusa (Delantero)', 20),
        ('Jens Petter Hauge (Delantero)', 25), ('Ola Solbakken (Delantero)', 25), ('Birger Meling (Defensa)', 30),
        ('Stefan Strandberg (Defensa)', 34), ('Marcus Holmgren Pedersen (Defensa)', 26), ('Even Hovland (Defensa)', 28),
        ('Tobias Borge (Mediocampista)', 25), ('Patrick Berg (Mediocampista)', 27), ('Odin Thiago Holm (Mediocampista)', 21),
        ('Isak Hansen-Aaroen (Mediocampista)', 20), ('Markus Henriksen (Mediocampista)', 33),
    ],
    'Argentina': [
        ('Emiliano Martinez (Portero)', 32), ('Geronimo Rulli (Portero)', 33), ('Walter Benitez (Portero)', 32),
        ('Cristian Romero (Defensa)', 26), ('Lisandro Martinez (Defensa)', 26), ('Nicolas Otamendi (Defensa)', 36),
        ('Nahuel Molina (Defensa)', 26), ('Nicolas Tagliafico (Defensa)', 32), ('Rodrigo De Paul (Mediocampista)', 30),
        ('Leandro Paredes (Mediocampista)', 30), ('Enzo Fernandez (Mediocampista)', 24), ('Alexis Mac Allister (Mediocampista)', 25),
        ('Lionel Messi (Delantero)', 39), ('Lautaro Martinez (Delantero)', 27), ('Julian Alvarez (Delantero)', 25),
        ('Angel Di Maria (Delantero)', 36), ('Paulo Dybala (Delantero)', 31), ('Alejandro Garnacho (Delantero)', 20),
        ('Valentin Carboni (Mediocampista)', 20), ('Thiago Almada (Mediocampista)', 23), ('Juan Foyth (Defensa)', 27),
        ('Marcos Acuna (Defensa)', 32), ('German Pezzella (Defensa)', 33), ('Exequiel Palacios (Mediocampista)', 26),
        ('Facundo Buonanotte (Mediocampista)', 20), ('Giovani Lo Celso (Mediocampista)', 28),
    ],
    'Argelia': [
        ('Rais M\'Bolhi (Portero)', 37), ('Alexandre Oukidja (Portero)', 34), ('Malik Asselah (Portero)', 28),
        ('Aissa Mandi (Defensa)', 33), ('Djamel Benlamri (Defensa)', 35), ('Ramy Bensebaini (Defensa)', 30),
        ('Youcef Atal (Defensa)', 28), ('Mehdi Tahrat (Defensa)', 28), ('Adlene Guedioura (Mediocampista)', 38),
        ('Nabil Bentaleb (Mediocampista)', 30), ('Sofiane Feghouli (Mediocampista)', 34), ('Ismail Bennacer (Mediocampista)', 27),
        ('Riyad Mahrez (Delantero)', 35), ('Islam Slimani (Delantero)', 36), ('Baghdad Bounedjah (Delantero)', 32),
        ('Andy Delort (Delantero)', 33), ('Yacine Brahimi (Mediocampista)', 34), ('Houssem Aouar (Mediocampista)', 27),
        ('Mohamed Amine Amoura (Delantero)', 24), ('Samir Merabet (Mediocampista)', 27), ('Abdelkader Bedrane (Defensa)', 29),
        ('Aymen Mahious (Delantero)', 27), ('Abdelkader Slimani (Mediocampista)', 30), ('Youcef Laouafi (Defensa)', 24),
        ('Taha Youcef Brahimi (Mediocampista)', 22), ('Zakaria Aboukhlal (Delantero)', 23),
    ],
    'Austria': [
        ('Patrick Pentz (Portero)', 27), ('Heinz Lindner (Portero)', 33), ('Alexander Schlager (Portero)', 30),
        ('David Alaba (Defensa)', 32), ('Stefan Posch (Defensa)', 27), ('Phillipp Lienhart (Defensa)', 28),
        ('Maximilian Woeber (Defensa)', 27), ('Andreas Ulmer (Defensa)', 38), ('Konrad Laimer (Mediocampista)', 27),
        ('Marcel Sabitzer (Mediocampista)', 30), ('Nicolas Seiwald (Mediocampista)', 24), ('Florian Grillitsch (Mediocampista)', 29),
        ('Christoph Baumgartner (Mediocampista)', 25), ('Marko Arnautovic (Delantero)', 35), ('Michael Gregoritsch (Delantero)', 30),
        ('Sasa Kalajdzic (Delantero)', 27), ('Guido Burgstaller (Delantero)', 35), ('Romano Schmid (Mediocampista)', 25),
        ('Xaver Schlager (Mediocampista)', 27), ('Peter Zulj (Mediocampista)', 31), ('Gernot Trauner (Defensa)', 32),
        ('Alexander Prass (Mediocampista)', 24), ('Philipp Mwene (Defensa)', 30), ('Stefan Ilsanker (Mediocampista)', 34),
        ('Lukas Susic (Mediocampista)', 22), ('Ercan Kara (Delantero)', 28),
    ],
    'Jordania': [
        ('Amer Shafi (Portero)', 35), ('Yazeed Abo Laila (Portero)', 27), ('Yosef Al-Husainat (Portero)', 26),
        ('Baher Madhoun (Defensa)', 30), ('Yazan Al-Arab (Defensa)', 28), ('Ahmad Al-Sarour (Defensa)', 27),
        ('Mousa Suleiman (Defensa)', 26), ('Hamza Al-Dardour (Delantero)', 29), ('Yazan Alnaib (Mediocampista)', 25),
        ('Abdallah Nasib (Mediocampista)', 28), ('Baha Faisal (Mediocampista)', 32), ('Musa Al-Taamari (Delantero)', 26),
        ('Ahmad Hayel (Delantero)', 30), ('Mohammad Al-Rosan (Mediocampista)', 24), ('Oday Dabbagh (Delantero)', 26),
        ('Mahmoud Al-Mardi (Mediocampista)', 24), ('Ehsan Haddad (Mediocampista)', 31), ('Khalil Bani Attiah (Defensa)', 27),
        ('Amer Doaij (Mediocampista)', 25), ('Saleh Hardalla (Defensa)', 26), ('Yacoub Abu Baker (Delantero)', 24),
        ('Nidal Dabbah (Delantero)', 28), ('Ezra Hendrick (Defensa)', 27), ('Sedrick Massing (Defensa)', 25),
        ('Zu\'bi Al-Rashdan (Mediocampista)', 30), ('Nawaf Al-Abed (Delantero)', 22),
    ],
    'Portugal': [
        ('Diogo Costa (Portero)', 25), ('Rui Patricio (Portero)', 36), ('Jose Sa (Portero)', 31),
        ('Ruben Dias (Defensa)', 27), ('Pepe (Defensa)', 41), ('Joao Cancelo (Defensa)', 30),
        ('Nuno Mendes (Defensa)', 22), ('Diogo Dalot (Defensa)', 25), ('Joao Palhinha (Mediocampista)', 29),
        ('Bruno Fernandes (Mediocampista)', 30), ('Bernardo Silva (Mediocampista)', 30), ('Vitinha (Mediocampista)', 24),
        ('Cristiano Ronaldo (Delantero)', 41), ('Rafael Leao (Delantero)', 25), ('Joao Felix (Delantero)', 25),
        ('Goncalo Ramos (Delantero)', 23), ('Pedro Neto (Delantero)', 25), ('Otavio (Mediocampista)', 30),
        ('Matheus Nunes (Mediocampista)', 26), ('Antonio Silva (Defensa)', 21), ('Danilo Pereira (Mediocampista)', 33),
        ('Francisco Conceicao (Delantero)', 22), ('Joao Neves (Mediocampista)', 20), ('Renato Sanches (Mediocampista)', 27),
        ('Ricardo Horta (Delantero)', 30), ('Diogo Jota (Delantero)', 28),
    ],
    'Congo DR': [
        ('Joel Kiassumbua (Portero)', 31), ('Ley Matampi (Portero)', 28), ('Ben Malango (Portero)', 27),
        ('Chancel Mbemba (Defensa)', 30), ('Theo Bongonda (Delantero)', 28), ('Arthur Masuaku (Defensa)', 30),
        ('Dylan Batubinsika (Defensa)', 26), ('Marcel Tisserand (Defensa)', 32), ('Chadrac Akolo (Delantero)', 29),
        ('Yoane Wissa (Delantero)', 28), ('Merveille Bokadi (Defensa)', 32), ('Elia Meschack (Mediocampista)', 24),
        ('Dieumerci Mbokani (Delantero)', 38), ('Silas Wissa (Delantero)', 26), ('Samuel Moutoussamy (Mediocampista)', 28),
        ('Firmin Mubele (Delantero)', 29), ('Kebano Neeskens (Mediocampista)', 32), ('Glody Ngonda (Mediocampista)', 24),
        ('Jordan Botaka (Delantero)', 32), ('Emmanuel Lebo (Defensa)', 26), ('Kiki Kouyate (Mediocampista)', 28),
        ('Yannick Bolasie (Delantero)', 34), ('Mariage Ndombe (Delantero)', 25), ('Papy Kimoto (Defensa)', 26),
        ('Cedric Bakambu (Delantero)', 33), ('Paul-Jose M\'poku (Mediocampista)', 32),
    ],
    'Uzbekistan': [
        ('Utkir Yusupov (Portero)', 29), ('Eldor Shomurodov (Delantero)', 28), ('Jasurbek Yakhshiboev (Portero)', 26),
        ('Dostonbek Khamdamov (Portero)', 24), ('Sanjar Tursunov (Defensa)', 31), ('Sherzod Nasrullayev (Defensa)', 27),
        ('Abbosbek Fayzullayev (Mediocampista)', 22), ('Jamshid Iskanderov (Defensa)', 28), ('Bekzod Kholmatov (Defensa)', 26),
        ('Otabek Shukurov (Mediocampista)', 25), ('Khurshid Makhmudov (Mediocampista)', 26), ('Doniyor Khusanov (Defensa)', 22),
        ('Odil Ahmedov (Mediocampista)', 36), ('Jaloliddin Masharipov (Mediocampista)', 30), ('Ulugbek Rashidov (Delantero)', 26),
        ('Azizbek Turgunboev (Mediocampista)', 23), ('Xasan Abdukholiqov (Delantero)', 24), ('Igor Sergeev (Delantero)', 29),
        ('Sherzod Kadirkulov (Defensa)', 27), ('Mirolim Tursunov (Mediocampista)', 22), ('Murodjon Yakhshiboev (Delantero)', 25),
        ('Sukhrob Kholiqov (Mediocampista)', 23), ('Zukhriddin Hamroyev (Defensa)', 24), ('Dostonbek Tursunov (Mediocampista)', 21),
        ('Bunyodbek Ziyadullayev (Delantero)', 22), ('Ravshan Irmatov (Mediocampista)', 22),
    ],
    'Colombia': [
        ('David Ospina (Portero)', 36), ('Camilo Vargas (Portero)', 34), ('Kevin Mier (Portero)', 25),
        ('Davinson Sanchez (Defensa)', 28), ('Yerry Mina (Defensa)', 30), ('Juan Cuadrado (Defensa)', 36),
        ('Daniel Munoz (Defensa)', 28), ('Johan Mojica (Defensa)', 32), ('Wilmar Barrios (Mediocampista)', 31),
        ('Mateus Uribe (Mediocampista)', 32), ('James Rodriguez (Mediocampista)', 33), ('Luis Diaz (Delantero)', 28),
        ('Duvan Zapata (Delantero)', 33), ('Rafael Santos Borre (Delantero)', 29), ('Luis Muriel (Delantero)', 33),
        ('Jhon Duran (Delantero)', 21), ('Richard Rios (Mediocampista)', 24), ('Jorge Carrascal (Mediocampista)', 27),
        ('Andres Andrade (Mediocampista)', 29), ('Santiago Arias (Defensa)', 32), ('Jefferson Lerma (Mediocampista)', 30),
        ('Miguel Angel Borja (Delantero)', 31), ('Rueda Lerma (Mediocampista)', 28), ('Carlos Cuesta (Defensa)', 25),
        ('Omar Bertel (Delantero)', 27), ('Jhon Janer Lucumi (Defensa)', 26),
    ],
    'Inglaterra': [
        ('Jordan Pickford (Portero)', 31), ('Nick Pope (Portero)', 33), ('Sam Johnstone (Portero)', 32),
        ('Kyle Walker (Defensa)', 34), ('Harry Maguire (Defensa)', 31), ('John Stones (Defensa)', 31),
        ('Luke Shaw (Defensa)', 29), ('Reece James (Defensa)', 25), ('Declan Rice (Mediocampista)', 26),
        ('Jude Bellingham (Mediocampista)', 21), ('Mason Mount (Mediocampista)', 26), ('Phil Foden (Mediocampista)', 24),
        ('Harry Kane (Delantero)', 31), ('Bukayo Saka (Delantero)', 23), ('Marcus Rashford (Delantero)', 27),
        ('Raheem Sterling (Delantero)', 31), ('Jack Grealish (Mediocampista)', 30), ('Jarrod Bowen (Delantero)', 28),
        ('Kobbie Mainoo (Mediocampista)', 19), ('Trent Alexander-Arnold (Defensa)', 26), ('Ben White (Defensa)', 27),
        ('Conor Gallagher (Mediocampista)', 25), ('Ollie Watkins (Delantero)', 29), ('Eberechi Eze (Mediocampista)', 26),
        ('Levi Colwill (Defensa)', 22), ('Cole Palmer (Mediocampista)', 22),
    ],
    'Croacia': [
        ('Dominik Livakovic (Portero)', 29), ('Lovre Kalinic (Portero)', 33), ('Ivica Ivusic (Portero)', 30),
        ('Dejan Lovren (Defensa)', 35), ('Josko Gvardiol (Defensa)', 23), ('Borna Sosa (Defensa)', 27),
        ('Duje Caleta-Car (Defensa)', 28), ('Josip Juranovic (Defensa)', 29), ('Luka Modric (Mediocampista)', 39),
        ('Marcelo Brozovic (Mediocampista)', 32), ('Mateo Kovacic (Mediocampista)', 30), ('Mario Pasalic (Mediocampista)', 29),
        ('Ivan Perisic (Delantero)', 35), ('Andrej Kramaric (Delantero)', 33), ('Bruno Petkovic (Delantero)', 31),
        ('Marko Livaja (Delantero)', 31), ('Borna Barisic (Defensa)', 30), ('Nikola Vlasic (Mediocampista)', 27),
        ('Martin Erlic (Defensa)', 27), ('Ante Budimir (Delantero)', 33), ('Kristijan Jakic (Mediocampista)', 26),
        ('Lovro Majer (Mediocampista)', 26), ('Ivan Gvardiol (Defensa)', 27), ('Antonio Marin (Mediocampista)', 24),
        ('Luka Ivanusec (Mediocampista)', 25), ('Petar Sucic (Mediocampista)', 21),
    ],
    'Ghana': [
        ('Lawrence Ati-Zigi (Portero)', 27), ('Abdul Manaf Nurudeen (Portero)', 25), ('Joseph Wollacott (Portero)', 28),
        ('Alexander Djiku (Defensa)', 29), ('Daniel Amartey (Defensa)', 30), ('Tariq Lamptey (Defensa)', 24),
        ('Gideon Mensah (Defensa)', 25), ('Denis Odoi (Defensa)', 36), ('Thomas Partey (Mediocampista)', 31),
        ('Baba Rahman (Defensa)', 30), ('Mohammed Kudus (Delantero)', 24), ('Daniel Kofi Kyereh (Mediocampista)', 28),
        ('Andre Ayew (Delantero)', 34), ('Jordan Ayew (Delantero)', 33), ('Inaki Williams (Delantero)', 30),
        ('Antoine Semenyo (Delantero)', 25), ('Elisha Owusu (Mediocampista)', 26), ('Kamaldeen Sulemana (Delantero)', 23),
        ('Osman Bukari (Delantero)', 26), ('Abdul Salis Samed (Mediocampista)', 24), ('Emmanuel Gyasi (Delantero)', 31),
        ('Ransford-Yeboah Konigsdorffer (Delantero)', 23), ('Mubarak Wakaso (Mediocampista)', 34),
        ('Ibrahim Danlad (Portero)', 22), ('Fatawu Issahaku (Mediocampista)', 21), ('Ernest Nuamah (Delantero)', 21),
    ],
    'Panama': [
        ('Luis Mejia (Portero)', 34), ('Orlando Mosquera (Portero)', 27), ('Gianluca Weston (Portero)', 23),
        ('Harold Cummings (Defensa)', 32), ('Fidel Escobar (Defensa)', 29), ('Andres Andrade (Defensa)', 29),
        ('Eric Davis (Defensa)', 31), ('Cesar Yanis (Defensa)', 29), ('Adalberto Carrasquilla (Mediocampista)', 26),
        ('Anibal Godoy (Mediocampista)', 36), ('Cristian Martinez (Mediocampista)', 26), ('Rolando Blackburn (Delantero)', 31),
        ('Gabriel Torres (Delantero)', 35), ('Ismael Diaz (Delantero)', 28), ('Jose Fajardo (Delantero)', 25),
        ('Cecilio Waterman (Delantero)', 28), ('Alfredo Stephens (Delantero)', 30), ('Alberto Quintero (Mediocampista)', 35),
        ('Edgardo Farina (Mediocampista)', 29), ('Ronaldo Vigil (Defensa)', 27), ('Michael Murillo (Defensa)', 29),
        ('Omar Browne (Delantero)', 29), ('Azmahar Ariano (Mediocampista)', 24), ('Jorge Ufarte (Mediocampista)', 25),
        ('Freddy Gondola (Delantero)', 22), ('Kevin Pineda (Mediocampista)', 23),
    ],
}


def grupo_por_nombre(nombre, paises_dict):
    return paises_dict.get(nombre)


class Command(BaseCommand):
    help = 'Carga los datos iniciales del Mundial 2026'

    def add_arguments(self, parser):
        parser.add_argument('--flush', action='store_true', help='Borrar datos existentes antes de cargar')

    @transaction.atomic
    def handle(self, *args, **options):
        if options['flush']:
            self.stdout.write('Borrando datos existentes...')
            GolPartido_model = None
            try:
                from polla.models import GolPartido
                GolPartido_model = GolPartido
            except ImportError:
                pass
            if GolPartido_model:
                GolPartido_model.objects.all().delete()
            Partido.objects.all().delete()
            Jugador.objects.all().delete()
            Pais.objects.all().delete()
            Estadio.objects.all().delete()
            Fase.objects.all().delete()

        # Fases
        self.stdout.write('Cargando fases...')
        for id_fase, desc in FASES:
            Fase.objects.get_or_create(id_fase=id_fase, defaults={'descripcion': desc})

        # Estadios
        self.stdout.write('Cargando estadios...')
        estadios_obj = {}
        for nombre in ESTADIOS:
            est, _ = Estadio.objects.get_or_create(nombre=nombre)
            estadios_obj[nombre] = est

        # Países
        self.stdout.write('Cargando países...')
        paises_obj = {}
        for nombre, grupo, emoji in PAISES:
            p, _ = Pais.objects.update_or_create(
                nombre=nombre,
                defaults={'grupo': grupo, 'emoji': emoji, 'es_campeon': False}
            )
            paises_obj[nombre] = p

        # Jugadores
        self.stdout.write('Cargando jugadores...')
        total_j = 0
        for nombre_pais, jugadores in JUGADORES.items():
            pais = paises_obj.get(nombre_pais)
            if not pais:
                self.stdout.write(self.style.WARNING(f'  País no encontrado: {nombre_pais}'))
                continue
            for nombre_j, edad in jugadores:
                Jugador.objects.get_or_create(
                    pais=pais,
                    nombre_completo=nombre_j,
                    defaults={'edad': edad}
                )
                total_j += 1

        self.stdout.write(f'  {total_j} jugadores cargados')

        # Partidos (Fase de Grupos — 72 partidos)
        self.stdout.write('Creando partidos de grupos...')
        fase_grupos = Fase.objects.get(id_fase=1)
        partidos_creados = 0

        # Cada grupo: 4 equipos, 6 partidos round-robin
        grupos = {}
        for nombre, grupo, _ in PAISES:
            if grupo not in grupos:
                grupos[grupo] = []
            if nombre in paises_obj:
                grupos[grupo].append(paises_obj[nombre])

        # Fechas de inicio de cada jornada por grupo (aproximadas)
        from datetime import date, time
        jornada_inicio = [
            date(2026, 6, 12),  # Jornada 1
            date(2026, 6, 17),  # Jornada 2
            date(2026, 6, 22),  # Jornada 3
        ]
        estadios_list = list(estadios_obj.values())

        estadio_idx = 0
        for g, equipos in sorted(grupos.items()):
            if len(equipos) < 4:
                continue
            a, b, c, d = equipos[:4]
            # Emparejamientos por jornada
            emparejamientos = [
                [(a, b), (c, d)],
                [(a, c), (b, d)],
                [(d, a), (b, c)],
            ]
            for j_idx, jornada in enumerate(emparejamientos):
                fecha_base = jornada_inicio[j_idx]
                for p_idx, (local, visitante) in enumerate(jornada):
                    estadio = estadios_list[estadio_idx % len(estadios_list)]
                    estadio_idx += 1
                    from datetime import datetime
                    hora = datetime.combine(fecha_base, time(18, 0))
                    tz_hora = timezone.make_aware(hora)
                    _, created = Partido.objects.get_or_create(
                        fase=fase_grupos,
                        pais_local=local,
                        pais_visitante=visitante,
                        defaults={
                            'estadio': estadio,
                            'fecha': tz_hora,
                            'jugado': False,
                        }
                    )
                    if created:
                        partidos_creados += 1

        self.stdout.write(f'  {partidos_creados} partidos creados')

        self.stdout.write(self.style.SUCCESS(
            f'\n✓ Datos cargados: 7 fases, {len(estadios_obj)} estadios, '
            f'{len(paises_obj)} países, {total_j} jugadores, {partidos_creados} partidos'
        ))
        self.stdout.write(self.style.WARNING(
            '\nRecuerda crear el superusuario:\n  python manage.py createsuperuser'
        ))
