document.addEventListener('DOMContentLoaded', () => {
    // Elements
    const dropArea = document.getElementById('dropArea');
    const fileInput = document.getElementById('fileInput');
    const uploadButton = document.getElementById('uploadButton');
    const uploadSection = document.getElementById('upload-section');
    const resultsSection = document.getElementById('results-section');
    const loadingOverlay = document.getElementById('loadingOverlay');
    const uploadedImage = document.getElementById('uploadedImage');
    const descriptionText = document.getElementById('descriptionText');
    const conceptionText = document.getElementById('conceptionText');
    const objectsList = document.getElementById('objectsList');
    const tabButtons = document.querySelectorAll('.tab-button');
    const tabContents = document.querySelectorAll('.tab-content');
    const conversationHistory = document.getElementById('conversationHistory');
    const questionInput = document.getElementById('questionInput');
    const askButton = document.getElementById('askButton');

    // New element references
    const redImpression = document.getElementById('redImpression');
    const greenImpression = document.getElementById('greenImpression');
    const blueImpression = document.getElementById('blueImpression');
    const generatePersonalizedBtn = document.getElementById('generatePersonalizedBtn');
    const personalizedDescription = document.getElementById('personalizedDescription');
    
    // Interpretation choice elements
    const basicInterpretation = document.getElementById('basicInterpretation');
    const personalizedInterpretation = document.getElementById('personalizedInterpretation');
    const colorImpressionSection = document.getElementById('colorImpressionSection');
    const confirmInterpretationBtn = document.getElementById('confirmInterpretationBtn');
    const conversationContainer = document.getElementById('conversation-container');
    const personalizedContent = document.querySelector('.personalized-content');
    
    // Variables
    let selectedFile = null;
    let artworkData = null;
    let hasPersonalizedDescription = false;
    let personalizedDescriptionText = '';
    let interpretationConfirmed = false;

    // Event listeners for drag and drop
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropArea.addEventListener(eventName, preventDefaults, false);
    });

    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    ['dragenter', 'dragover'].forEach(eventName => {
        dropArea.addEventListener(eventName, () => {
            dropArea.classList.add('active');
        });
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropArea.addEventListener(eventName, () => {
            dropArea.classList.remove('active');
        });
    });

    dropArea.addEventListener('drop', handleDrop, false);
    dropArea.addEventListener('click', () => fileInput.click());
    fileInput.addEventListener('change', handleFileSelect);
    uploadButton.addEventListener('click', uploadFile);
    askButton.addEventListener('click', askQuestion);
    questionInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') askQuestion();
    });

    // Add event listeners for interpretation choice
    basicInterpretation.addEventListener('change', updateInterpretationUI);
    personalizedInterpretation.addEventListener('change', updateInterpretationUI);
    confirmInterpretationBtn.addEventListener('click', confirmInterpretation);
    
    // Add event listener for personalized description
    generatePersonalizedBtn.addEventListener('click', generatePersonalizedDescription);

    // Tab functionality
    tabButtons.forEach(button => {
        button.addEventListener('click', () => {
            const tabName = button.dataset.tab;
            
            tabButtons.forEach(btn => btn.classList.remove('active'));
            tabContents.forEach(content => content.classList.remove('active'));
            
            button.classList.add('active');
            document.getElementById(tabName).classList.add('active');
        });
    });

    // Handle file drop
    function handleDrop(e) {
        const dt = e.dataTransfer;
        const files = dt.files;
        
        if (files.length > 0) {
            handleFile(files[0]);
        }
    }

    // Handle file selection from input
    function handleFileSelect(e) {
        const files = e.target.files;
        
        if (files.length > 0) {
            handleFile(files[0]);
        }
    }

    // Process the selected file
    function handleFile(file) {
        if (!file.type.match('image.*')) {
            alert('請上傳圖片檔案');
            return;
        }
        
        selectedFile = file;
        
        // Create a preview (optional)
        const reader = new FileReader();
        reader.onload = function(e) {
            dropArea.innerHTML = `<img src="${e.target.result}" alt="Preview" style="max-width: 100%; max-height: 200px;">`;
        };
        reader.readAsDataURL(file);
        
        uploadButton.disabled = false;
    }

    // Upload the file to the server
    function uploadFile() {
        if (!selectedFile) return;
        
        const formData = new FormData();
        formData.append('file', selectedFile);
        
        // No longer need to get color impressions during initial upload
        // as they've been removed from the first page
        formData.append('color_impressions', JSON.stringify({}));
        
        // Show loading overlay
        loadingOverlay.classList.remove('hidden');
        
        fetch('/upload', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                artworkData = data.data;  // Store artwork data for later use
                displayResults(data);
            } else {
                alert('上傳失敗: ' + data.error);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('上傳過程發生錯誤，請重試');
        })
        .finally(() => {
            loadingOverlay.classList.add('hidden');
        });
    }

    // Display the analysis results
    function displayResults(data) {
        // Switch to results view
        uploadSection.classList.add('hidden');
        resultsSection.classList.remove('hidden');
        
        // Set the image
        uploadedImage.src = data.image_url;
        
        // Fill in the analysis data
        descriptionText.textContent = data.data.description;
        conceptionText.textContent = data.data.artistic_conception;
        
        // Create object tags
        objectsList.innerHTML = '';
        if (data.data.object && Array.isArray(data.data.object)) {
            data.data.object.forEach(obj => {
                for (const [item, color] of Object.entries(obj)) {
                    const tag = document.createElement('div');
                    tag.className = 'object-tag';
                    
                    // Apply color styling to the tag
                    const colorValue = getColorValue(color);
                    
                    // Apply color as background with slight transparency
                    tag.style.backgroundColor = `${colorValue}30`; // 30 is hex for ~20% opacity
                    tag.style.borderColor = colorValue;
                    
                    tag.innerHTML = `
                        <span class="color-dot" style="background-color: ${colorValue};"></span>
                        <span style="color: #2d3748;">${item}</span>
                    `;
                    objectsList.appendChild(tag);
                }
            });
        }
        
        // Don't add initial assistant message yet - wait for user to choose interpretation type
        conversationContainer.classList.add('hidden');
    }
    
    // Update UI based on interpretation choice
    function updateInterpretationUI() {
        if (personalizedInterpretation.checked) {
            colorImpressionSection.classList.remove('hidden');
            if (hasPersonalizedDescription) {
                confirmInterpretationBtn.disabled = false;
            } else {
                confirmInterpretationBtn.disabled = true; // Disable confirm until personalized description is generated
            }
        } else {
            colorImpressionSection.classList.add('hidden');
            confirmInterpretationBtn.disabled = false;
        }
    }
    
    // Confirm interpretation choice and start conversation
    function confirmInterpretation() {
        if (personalizedInterpretation.checked && !hasPersonalizedDescription) {
            alert('請先生成個人化解讀');
            return;
        }
        
        interpretationConfirmed = true;
        conversationContainer.classList.remove('hidden');
        
        // Initialize conversation history
        conversationHistory.innerHTML = '';
        
        // Add initial message based on interpretation type
        if (personalizedInterpretation.checked) {
            addMessage('assistant', `根據你的顏色印象，我對這幅畫作有了個人化的解讀：\n\n${personalizedDescriptionText}\n\n你可以問我關於這幅畫的任何問題。`);
        } else {
            addMessage('assistant', `我已經分析了這幅畫作，以下是基本描述：\n\n${artworkData.description}\n\n意境：${artworkData.artistic_conception}\n\n你可以問我關於這幅畫的任何細節。`);
        }
        
        // Disable the interpretation choice sections
        const interpretationOptions = document.querySelectorAll('.interpretation-option');
        interpretationOptions.forEach(option => {
            option.classList.add('disabled-section');
        });
        colorImpressionSection.classList.add('disabled-section');
        confirmInterpretationBtn.disabled = true;
        
        // Scroll to conversation
        conversationContainer.scrollIntoView({ behavior: 'smooth' });
        
        // Focus on question input
        questionInput.focus();
    }

    // Helper function to convert color names to hex values
    function getColorValue(colorName) {
        const colorMap = {
            // Basic colors
            '紅色': '#e53e3e',
            '藍色': '#3182ce',
            '綠色': '#38a169',
            '黃色': '#ecc94b',
            '橙色': '#ed8936',
            '紫色': '#805ad5',
            '粉色': '#ed64a6',
            '棕色': '#8b4513',
            '灰色': '#718096',
            '黑色': '#2d3748',
            '白色': '#ffffff',
            
            // Light variants
            '淺紅色': '#fc8181',
            '淺藍色': '#63b3ed',
            '淺綠色': '#68d391',
            '淺黃色': '#faf089',
            '淺橙色': '#fbd38d',
            '淺紫色': '#b794f4',
            '淺粉色': '#f687b3',
            '淺棕色': '#bc8a5f',
            '淺灰色': '#cbd5e0',
            
            // Dark variants
            '深紅色': '#c53030',
            '深藍色': '#2c5282',
            '深綠色': '#2f855a',
            '深黃色': '#d69e2e',
            '深橙色': '#c05621',
            '深紫色': '#6b46c1',
            '深粉色': '#b83280',
            '深棕色': '#654321',
            '深灰色': '#4a5568',
        };
        
        // Try to find the exact match
        for (const [key, value] of Object.entries(colorMap)) {
            if (colorName.includes(key)) {
                return value;
            }
        }
        
        // Default fallback
        return '#718096';
    }

    // Helper function to determine if text should be white or black based on background color
    function getContrastColor(hexColor) {
        // Convert hex to RGB
        const r = parseInt(hexColor.slice(1, 3), 16);
        const g = parseInt(hexColor.slice(3, 5), 16);
        const b = parseInt(hexColor.slice(5, 7), 16);
        
        // Calculate perceived brightness (YIQ equation)
        const yiq = ((r * 299) + (g * 587) + (b * 114)) / 1000;
        
        // Return black or white depending on brightness
        return (yiq >= 150) ? '#2d3748' : '#ffffff';
    }

    // Generate personalized description based on color impressions
    function generatePersonalizedDescription() {
        // Get current color impressions
        const colorImpressions = {
            red: redImpression.value.trim(),
            green: greenImpression.value.trim(),
            blue: blueImpression.value.trim()
        };
        
        if (!colorImpressions.red && !colorImpressions.green && !colorImpressions.blue) {
            alert('請至少填寫一種顏色的印象');
            return;
        }
        
        // Disable button and show loading state
        generatePersonalizedBtn.disabled = true;
        personalizedDescription.textContent = '正在生成個人化描述...';
        personalizedContent.classList.remove('hidden');
        
        fetch('/personalize', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ color_impressions: colorImpressions })
        })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                personalizedDescription.textContent = `錯誤: ${data.error}`;
                hasPersonalizedDescription = false;
            } else {
                personalizedDescription.textContent = data.personalized_description;
                personalizedDescriptionText = data.personalized_description;
                hasPersonalizedDescription = true;
                
                // If personalized interpretation is selected, enable confirm button
                if (personalizedInterpretation.checked) {
                    confirmInterpretationBtn.disabled = false;
                }
            }
        })
        .catch(error => {
            console.error('Error:', error);
            personalizedDescription.textContent = '生成個人化描述時發生錯誤，請重試';
            hasPersonalizedDescription = false;
        })
        .finally(() => {
            // Always re-enable the button regardless of success or failure
            generatePersonalizedBtn.disabled = false;
        });
    }

    // Ask a follow-up question
    function askQuestion() {
        const question = questionInput.value.trim();
        if (!question) return;
        
        if (!interpretationConfirmed) {
            alert('請先確認解讀方式');
            return;
        }
        
        addMessage('user', question);
        questionInput.value = '';
        questionInput.disabled = true;
        askButton.disabled = true;
        
        // Prepare request payload
        const payload = {
            question: question
        };
        
        // If using personalized interpretation, include it in the request
        if (personalizedInterpretation.checked && hasPersonalizedDescription) {
            payload.personalized_description = personalizedDescriptionText;
            payload.use_personalized = true;
        }
        
        fetch('/ask', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(payload)
        })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                addMessage('assistant', `錯誤: ${data.error}`);
            } else {
                addMessage('assistant', data.answer);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            addMessage('assistant', '處理請求時發生錯誤，請重試');
        })
        .finally(() => {
            questionInput.disabled = false;
            askButton.disabled = false;
            questionInput.focus();
        });
    }

    // Add a message to the conversation history
    function addMessage(role, content) {
        const message = document.createElement('div');
        message.className = `message ${role}-message`;
        
        // Process line breaks and format text
        const formattedContent = content.replace(/\n/g, '<br>');
        message.innerHTML = formattedContent;
        
        conversationHistory.appendChild(message);
        conversationHistory.scrollTop = conversationHistory.scrollHeight;
    }
});
