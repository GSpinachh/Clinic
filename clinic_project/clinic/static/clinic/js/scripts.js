document.addEventListener('DOMContentLoaded', function() {
    document.getElementById('id_specialty').addEventListener('change', function() {
        const specialtyId = this.value;
        const doctorSelect = document.getElementById('id_doctor');
        
        if (specialtyId) {
            fetch(`/get-doctors/?specialty_id=${specialtyId}`)
                .then(response => response.json())
                .then(data => {
                    doctorSelect.innerHTML = '';
                    if (data.length > 0) {
                        data.forEach(doctor => {
                            const option = document.createElement('option');
                            option.value = doctor.id;
                            option.textContent = doctor.name;
                            doctorSelect.appendChild(option);
                        });
                    } else {
                        const option = document.createElement('option');
                        option.textContent = 'Нет доступных врачей';
                        doctorSelect.appendChild(option);
                    }
                });
        } else {
            doctorSelect.innerHTML = '<option value="">Сначала выберите специальность</option>';
        }
    });
    
    // Календарь и время
    const dateInput = document.getElementById('id_date');
    if (dateInput) {
        dateInput.addEventListener('change', function() {
            // !!!
        });
    }
});