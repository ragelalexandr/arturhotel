// reports.js

// Визуализация для статистики бронирований
function renderActiveBookingsChart(stats) {
    console.log(stats);
    const activeBookingsData = {
        labels: stats.map(stat => stat.room_id),
        datasets: [{
            label: 'Активные бронирования',
            data: stats.map(stat => stat.active_bookings),
            backgroundColor: 'rgba(54, 162, 235, 0.2)',
            borderColor: 'rgba(54, 162, 235, 1)',
            borderWidth: 1
        }]
    };

    // Создание графика
    new Chart(document.getElementById('activeBookingsChart'), {
        type: 'bar',
        data: activeBookingsData
    });
}

// Визуализация для популярности номеров
function renderPopularRoomsChart(popularRooms) {
    console.log(popularRooms);
    const popularRoomsData = {
        labels: popularRooms.map(room => room.room_id),
        datasets: [{
            label: 'Популярность номеров',
            data: popularRooms.map(room => room.total_bookings),
            backgroundColor: 'rgba(255, 206, 86, 0.2)',
            borderColor: 'rgba(255, 206, 86, 1)',
            borderWidth: 1
        }]
    };

    // Создание графика
    new Chart(document.getElementById('popularRoomsChart'), {
        type: 'bar',
        data: popularRoomsData
    });
}

// Визуализация для загрузки номеров
function renderRoomLoadChart(roomLoad) {
    console.log(roomLoad);
    const roomLoadData = {
        labels: roomLoad.map(load => load.type),
        datasets: [{
            label: 'Доступные номера',
            data: roomLoad.map(load => load.available_rooms),
            backgroundColor: 'rgba(75, 192, 192, 0.2)',
            borderColor: 'rgba(75, 192, 192, 1)',
            borderWidth: 1
        }, {
            label: 'Недоступные номера',
            data: roomLoad.map(load => load.unavailable_rooms),
            backgroundColor: 'rgba(255, 99, 132, 0.2)',
            borderColor: 'rgba(255, 99, 132, 1)',
            borderWidth: 1
        }]
    };

    // Создание графика
    new Chart(document.getElementById('roomLoadChart'), {
        type: 'bar',
        data: roomLoadData
    });
}
