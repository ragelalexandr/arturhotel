from graphviz import Digraph

dot = Digraph(comment='Detailed ER Diagram', format='png')

# Настройка формата узлов — используем HTML-теги для детального представления
# Таблица rooms
dot.node('rooms', r'''<
<TABLE BORDER="0" CELLBORDER="1" CELLSPACING="0">
  <TR><TD COLSPAN="2" BGCOLOR="#b3cde0"><B>rooms</B></TD></TR>
  <TR><TD>id (PK)</TD><TD>INTEGER AUTOINCREMENT</TD></TR>
  <TR><TD>type</TD><TD>TEXT NOT NULL</TD></TR>
  <TR><TD>capacity</TD><TD>INTEGER</TD></TR>
  <TR><TD>amenities</TD><TD>TEXT</TD></TR>
  <TR><TD>price</TD><TD>REAL</TD></TR>
  <TR><TD>photo</TD><TD>TEXT</TD></TR>
  <TR><TD>available</TD><TD>INTEGER DEFAULT 1</TD></TR>
</TABLE>>''')

# Таблица bookings
dot.node('bookings', r'''<
<TABLE BORDER="0" CELLBORDER="1" CELLSPACING="0">
  <TR><TD COLSPAN="2" BGCOLOR="#ccebc5"><B>bookings</B></TD></TR>
  <TR><TD>id (PK)</TD><TD>INTEGER AUTOINCREMENT</TD></TR>
  <TR><TD>guest_id (FK)</TD><TD>INTEGER NOT NULL</TD></TR>
  <TR><TD>room_id (FK)</TD><TD>INTEGER NOT NULL</TD></TR>
  <TR><TD>start_date</TD><TD>DATE NOT NULL</TD></TR>
  <TR><TD>end_date</TD><TD>DATE NOT NULL</TD></TR>
  <TR><TD>status</TD><TD>TEXT DEFAULT 'active'</TD></TR>
</TABLE>>''')

# Таблица guests
dot.node('guests', r'''<
<TABLE BORDER="0" CELLBORDER="1" CELLSPACING="0">
  <TR><TD COLSPAN="2" BGCOLOR="#decbe4"><B>guests</B></TD></TR>
  <TR><TD>id (PK)</TD><TD>INTEGER AUTOINCREMENT</TD></TR>
  <TR><TD>name</TD><TD>TEXT NOT NULL</TD></TR>
  <TR><TD>contact</TD><TD>TEXT</TD></TR>
  <TR><TD>preferences</TD><TD>TEXT</TD></TR>
  <TR><TD>history</TD><TD>TEXT</TD></TR>
</TABLE>>''')

# Таблица reviews
dot.node('reviews', r'''<
<TABLE BORDER="0" CELLBORDER="1" CELLSPACING="0">
  <TR><TD COLSPAN="2" BGCOLOR="#fbb4ae"><B>reviews</B></TD></TR>
  <TR><TD>id (PK)</TD><TD>INTEGER AUTOINCREMENT</TD></TR>
  <TR><TD>guest_id (FK)</TD><TD>INTEGER NOT NULL</TD></TR>
  <TR><TD>review</TD><TD>TEXT</TD></TR>
  <TR><TD>rating</TD><TD>INTEGER (1-5)</TD></TR>
  <TR><TD>admin_reply</TD><TD>TEXT</TD></TR>
  <TR><TD>moderated</TD><TD>INTEGER DEFAULT 0</TD></TR>
</TABLE>>''')

# Таблица recommendations
dot.node('recommendations', r'''<
<TABLE BORDER="0" CELLBORDER="1" CELLSPACING="0">
  <TR><TD COLSPAN="2" BGCOLOR="#fddaec"><B>recommendations</B></TD></TR>
  <TR><TD>id (PK)</TD><TD>INTEGER AUTOINCREMENT</TD></TR>
  <TR><TD>guest_id (FK)</TD><TD>INTEGER NOT NULL</TD></TR>
  <TR><TD>room_id (FK)</TD><TD>INTEGER NOT NULL</TD></TR>
  <TR><TD>reason</TD><TD>TEXT</TD></TR>
</TABLE>>''')

# Таблица staff
dot.node('staff', r'''<
<TABLE BORDER="0" CELLBORDER="1" CELLSPACING="0">
  <TR><TD COLSPAN="2" BGCOLOR="#ffffcc"><B>staff</B></TD></TR>
  <TR><TD>id (PK)</TD><TD>INTEGER AUTOINCREMENT</TD></TR>
  <TR><TD>name</TD><TD>TEXT NOT NULL</TD></TR>
  <TR><TD>role</TD><TD>TEXT</TD></TR>
  <TR><TD>tasks</TD><TD>TEXT</TD></TR>
</TABLE>>''')

# Таблица task_reports
dot.node('task_reports', r'''<
<TABLE BORDER="0" CELLBORDER="1" CELLSPACING="0">
  <TR><TD COLSPAN="2" BGCOLOR="#fed9a6"><B>task_reports</B></TD></TR>
  <TR><TD>id (PK)</TD><TD>INTEGER AUTOINCREMENT</TD></TR>
  <TR><TD>staff_id (FK)</TD><TD>INTEGER NOT NULL</TD></TR>
  <TR><TD>task</TD><TD>TEXT NOT NULL</TD></TR>
  <TR><TD>status</TD><TD>TEXT DEFAULT 'pending'</TD></TR>
  <TR><TD>completed_at</TD><TD>DATETIME</TD></TR>
</TABLE>>''')

# Определяем отношения между таблицами с указанием внешних ключей и направлений связей
# bookings: связь с guests и rooms
dot.edge('guests', 'bookings', label='guest_id\n(ON DELETE CASCADE)')
dot.edge('rooms', 'bookings', label='room_id\n(ON DELETE SET NULL)')

# reviews: связь с guests
dot.edge('guests', 'reviews', label='guest_id\n(ON DELETE CASCADE)')

# recommendations: связь с guests и rooms
dot.edge('guests', 'recommendations', label='guest_id\n(ON DELETE CASCADE)')
dot.edge('rooms', 'recommendations', label='room_id\n(ON DELETE CASCADE)')

# task_reports: связь со staff
dot.edge('staff', 'task_reports', label='staff_id\n(ON DELETE CASCADE)')

# Сохранение и просмотр диаграммы
dot.render('detailed_er_diagram', view=True)
