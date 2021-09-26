
CREATE TABLE users
(
    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL,
    password TEXT NOT NULL
);

CREATE TABLE bookings
(
    booking_id INTEGER PRIMARY KEY AUTOINCREMENT,
    trainer INTEGER NOT NULL,
    session_type INTEGER NOT NULL,
    client INTEGER NOT NULL,
    price INTEGER NOT NULL,
    end_time DATETIME NOT NULL,
    booking_date DATETIME NOT NULL,
    booked_at DATETIME NOT NULL
);

CREATE TABLE services
(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    activity TEXT NOT NULL
);

CREATE TABLE trainerPref
(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trainer_id INTEGER NOT NULL,
    activity INTEGER NOT NULL,
    price INTEGER NOT NULL
);

CREATE TABLE wanted_act
(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    activity TEXT NOT NULL
);
