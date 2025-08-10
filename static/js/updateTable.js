const socket = io();

// Poll for updates every second
setInterval(() => socket.emit('request_update'), 1000);

socket.on('update_element', data => {
const [rowIndex, newStatus] = Object.values(data);
const cell = document
.getElementById("myTable")
.rows[rowIndex]
.cells[2];

// Edit the cell with the new status and add the dot
cell.className = 'status'; 
cell.innerHTML = `<span class="status-dot ${newStatus.toLowerCase()}"></span>${newStatus}`;});
