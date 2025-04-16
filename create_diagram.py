from graphviz import Source

# Определяем диаграмму последовательности в синтаксисе PlantUML
plantuml_code = """
@startuml
actor Guest
participant "Booking System" as BS
participant "Room Database" as DB

Guest -> BS : Request booking (dates, room type)
BS -> DB : Check room availability
DB --> BS : Room available?
alt Room available
    BS -> DB : Create booking record
    BS --> Guest : Send confirmation
else Room not available
    BS --> Guest : Send "No rooms available"
end
@enduml
"""

# Генерируем и сохраняем диаграмму
diagram = Source(plantuml_code)
diagram.render("sequence_diagram", format="png", view=True)
