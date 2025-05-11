async function uploadAndProcess() {
    const fileInput = document.getElementById('csv_upload');
    const file = fileInput.files[0];
    const labelsContainer = document.getElementById('labels_container');
    labelsContainer.innerHTML = ''; // Clear previous labels

    if (file) {
        const formData = new FormData();
        formData.append('csv_file', file);

        try {
            const response = await fetch('/process_csv', {
                method: 'POST',
                body: formData
            });
            const data = await response.json();

            if (data.error) {
                labelsContainer.innerText = `Error: ${data.error}`;
            } else if (data.labels) {
                data.labels.forEach(labelData => {
                    const labelDiv = document.createElement('div');
                    labelDiv.classList.add('meal-label');
                    labelDiv.innerHTML = `
                        <h3>${labelData.customer_first_name} ${labelData.customer_last_name}</h3>
                        <p><strong>Product:</strong> ${labelData.product} ${labelData.variant}</p>
                        ${labelData.modifiers ? `<p><strong>Modifiers:</strong> ${labelData.modifiers}</p>` : ''}
                        <p><strong>Price:</strong> $${labelData.price}</p>
                        <p><strong>Expiry Date:</strong> ${labelData.expiry_date}</p>
                        <p><strong>Calories:</strong> ${labelData.calories}</p>
                        <p><strong>Protein:</strong> ${labelData.protein}g</p>
                        <p><strong>Carbs:</strong> ${labelData.carbs}g</p>
                        <p><strong>Fat:</strong> ${labelData.fat}g</p>
                        <p><strong>Preparation:</strong> ${labelData.preparation}</p>
                        <hr>
                    `;
                    labelsContainer.appendChild(labelDiv);
                });
            }
        } catch (error) {
            labelsContainer.innerText = `Error: ${error}`;
        }
    } else {
        labelsContainer.innerText = 'Please upload a CSV file.';
    }
}