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
    const conversationHistory = document.getElementById('conversationHistory');
    const questionInput = document.getElementById('questionInput');
    const askButton = document.getElementById('askButton');

    // 添加顏色印象輸入元素引用
    const redImpression = document.getElementById('redImpression');
    const greenImpression = document.getElementById('greenImpression');
    const blueImpression = document.getElementById('blueImpression');
    
    // Add country selection element reference
    const countrySelect = document.getElementById('countrySelect');
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
    let selectedCountry = ''; // Add variable to store selected country
    let interpretationConfirmed = false;
    let conversationId = null; // Add global variable to store conversation_id

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

    // Listen for country selection changes
    countrySelect.addEventListener('change', function() {
        selectedCountry = this.value;
        // Enable/disable personalized description generation button
        updateGenerateButtonState();
    });

    // 更新生成按鈕狀態的函數
    function updateGenerateButtonState() {
        generatePersonalizedBtn.disabled = !selectedCountry;
    }

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
        
        // 收集顏色印象到一個對象中
        const colorImpressions = {
            red: redImpression.value.trim(),
            green: greenImpression.value.trim(),
            blue: blueImpression.value.trim()
        };
        
        formData.append('color_impressions', JSON.stringify(colorImpressions));
        
        // Show loading overlay
        loadingOverlay.classList.remove('hidden');
        
        fetch('/upload', {
            method: 'POST',
            body: formData,
            credentials: 'same-origin'  // Ensure cookies are sent and received
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                artworkData = data.data;  // Store artwork data for later use
                // Save conversation_id
                conversationId = data.conversation_id || data.data.conversation_id;
                console.log("接收到的conversation_id: ", conversationId);
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
        
        // Fill in the analysis data - only description now
        descriptionText.textContent = data.data.description;
        
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
            addMessage('assistant', `根據你的所屬國家，我對這幅畫作有了個人化的解讀：\n\n${personalizedDescriptionText}\n\n你可以問我關於這幅畫的任何問題。`);
        } else {
            addMessage('assistant', `我已經分析了這幅畫作，以下是基本描述：\n\n${artworkData.description}\n\n你可以問我關於這幅畫的任何細節。`);
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

    // Generate personalized description based on selected country
    function generatePersonalizedDescription() {
        // Check if a country is selected
        if (!selectedCountry) {
            alert('請選擇您的所屬國家');
            return;
        }
        
        // Disable button and show loading state
        generatePersonalizedBtn.disabled = true;
        personalizedDescription.textContent = '正在生成個人化描述...';
        personalizedContent.classList.remove('hidden');

        // 收集顏色印象
        const colorImpressions = {
            red: redImpression.value.trim(),
            green: greenImpression.value.trim(),
            blue: blueImpression.value.trim()
        };

        console.log("conversation_id: ", conversationId);
        fetch('/personalize', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ 
                personalized_data: selectedCountry,
                conversation_id: conversationId,  // Add conversation_id
                color_impressions: colorImpressions  // 添加顏色印象數據
            }),
            credentials: 'same-origin'  // Ensure cookies are sent and received
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
            question: question,
            conversation_id: conversationId  // Add conversation_id to the request
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
            body: JSON.stringify(payload),
            credentials: 'same-origin'  // Ensure cookies are sent and received
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
