from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS
import os
import tempfile
import PyPDF2
import docx
from openai import OpenAI
import logging

app = Flask(__name__)
CORS(app)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

# Configure upload settings
UPLOAD_FOLDER = tempfile.mkdtemp()
ALLOWED_EXTENSIONS = {'pdf', 'docx'}
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def extract_text_from_pdf(file_path):
    """Extract text from PDF file"""
    try:
        with open(file_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
        return text
    except Exception as e:
        logger.error(f"Error extracting PDF text: {str(e)}")
        return None

def extract_text_from_docx(file_path):
    """Extract text from DOCX file"""
    try:
        doc = docx.Document(file_path)
        text = ""
        for paragraph in doc.paragraphs:
            text += paragraph.text + "\n"
        return text
    except Exception as e:
        logger.error(f"Error extracting DOCX text: {str(e)}")
        return None

def analyze_resume_with_openai(resume_text):
    """Analyze resume using OpenAI API or mock analysis"""
    
    # Check if we want to use mock mode (set USE_MOCK=true in environment)
    if os.getenv('USE_MOCK', '').lower() == 'true':
        return generate_mock_feedback(resume_text)
    
    try:
        prompt = f"""
        Please analyze the following resume and provide detailed, constructive feedback. 
        Focus on these areas:
        
        1. Overall Structure and Format
        2. Professional Summary/Objective
        3. Work Experience descriptions
        4. Skills section
        5. Education section
        6. Achievements and quantifiable results
        7. Keywords and ATS optimization
        8. Areas for improvement
        9. Strengths to highlight
        10. Overall rating (1-10)
        
        Resume content:
        {resume_text}
        
        Please provide specific, actionable feedback in a well-structured format.
        """
        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an expert resume reviewer and career counselor with extensive experience in hiring and recruitment."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=800,  # Reduced tokens to save costs
            temperature=0.7
        )
        
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"Error with OpenAI API: {str(e)}")
        # Fall back to mock if API fails
        return generate_mock_feedback(resume_text)

def generate_mock_feedback(resume_text):
    """Generate mock feedback for testing purposes"""
    word_count = len(resume_text.split())
    
    return f"""
📋 RESUME ANALYSIS REPORT (Demo Mode)

🔍 OVERALL ASSESSMENT
Your resume has been analyzed with {word_count} words of content. Here's your comprehensive feedback:

⭐ OVERALL RATING: 7.5/10

📝 STRUCTURE & FORMAT
✅ Strengths:
- Document appears well-organized
- Content length is appropriate for review

⚠️ Areas for Improvement:
- Consider using consistent formatting throughout
- Ensure proper spacing and alignment
- Use professional fonts (Arial, Calibri, or Times New Roman)

💼 PROFESSIONAL SUMMARY
- Add a compelling 2-3 line summary at the top
- Include key skills and years of experience
- Tailor summary to target job roles

🏢 WORK EXPERIENCE
- Use action verbs to start each bullet point
- Include quantifiable achievements (numbers, percentages, dollar amounts)
- Focus on results rather than just responsibilities
- Ensure dates are consistent and properly formatted

🛠️ SKILLS SECTION
- Separate technical skills from soft skills
- Include relevant industry keywords
- Rate proficiency levels if appropriate
- Remove outdated or irrelevant skills

🎓 EDUCATION
- Include relevant coursework if recent graduate
- Add GPA if 3.5 or higher
- Include certifications and professional development

🎯 ATS OPTIMIZATION
- Include industry-specific keywords
- Use standard section headings
- Avoid graphics, tables, or complex formatting
- Save as both PDF and Word formats

📈 KEY RECOMMENDATIONS:
1. Add measurable achievements to each role
2. Customize resume for each job application
3. Include relevant keywords from job descriptions
4. Keep to 1-2 pages maximum
5. Proofread for grammar and spelling errors

💡 NEXT STEPS:
- Research target companies and roles
- Network within your industry
- Practice your elevator pitch
- Prepare for common interview questions

Note: This is demo mode. Enable OpenAI integration for detailed AI analysis.
    """

@app.route('/')
def index():
    """Serve the HTML frontend"""
    return render_template_string(HTML_TEMPLATE)

@app.route('/upload', methods=['POST'])
def upload_resume():
    """Handle resume upload and analysis"""
    try:
        # Check if file was uploaded
        if 'resume' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400
        
        file = request.files['resume']
        
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'error': 'Invalid file type. Please upload PDF or DOCX files only.'}), 400
        
        # Save uploaded file
        filename = file.filename
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        
        # Extract text based on file type
        file_extension = filename.rsplit('.', 1)[1].lower()
        
        if file_extension == 'pdf':
            resume_text = extract_text_from_pdf(file_path)
        elif file_extension == 'docx':
            resume_text = extract_text_from_docx(file_path)
        else:
            return jsonify({'error': 'Unsupported file type'}), 400
        
        if not resume_text:
            return jsonify({'error': 'Could not extract text from file'}), 400
        
        if len(resume_text.strip()) < 50:
            return jsonify({'error': 'Resume content appears to be too short or empty'}), 400
        
        # Analyze resume with OpenAI
        feedback = analyze_resume_with_openai(resume_text)
        
        # Clean up uploaded file
        os.remove(file_path)
        
        return jsonify({
            'success': True,
            'filename': filename,
            'feedback': feedback
        })
        
    except Exception as e:
        logger.error(f"Error processing upload: {str(e)}")
        return jsonify({'error': f'Error processing file: {str(e)}'}), 500

# HTML Template
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Resume Analyzer</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        
        .container {
            max-width: 800px;
            margin: 0 auto;
            background: white;
            border-radius: 15px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
            overflow: hidden;
        }
        
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }
        
        .header h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
        }
        
        .header p {
            font-size: 1.1em;
            opacity: 0.9;
        }
        
        .upload-section {
            padding: 40px;
            text-align: center;
        }
        
        .dropzone {
            border: 3px dashed #667eea;
            border-radius: 10px;
            padding: 60px 40px;
            margin: 20px 0;
            background: #f8f9ff;
            transition: all 0.3s ease;
            cursor: pointer;
        }
        
        .dropzone:hover {
            border-color: #764ba2;
            background: #f0f2ff;
        }
        
        .dropzone.dragover {
            border-color: #764ba2;
            background: #e8ebff;
            transform: scale(1.02);
        }
        
        .upload-icon {
            font-size: 4em;
            color: #667eea;
            margin-bottom: 20px;
        }
        
        .upload-text {
            font-size: 1.2em;
            color: #333;
            margin-bottom: 10px;
        }
        
        .upload-subtext {
            color: #666;
            font-size: 0.9em;
        }
        
        #fileInput {
            display: none;
        }
        
        .btn {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 12px 30px;
            border-radius: 25px;
            font-size: 1em;
            cursor: pointer;
            transition: all 0.3s ease;
            margin: 10px;
        }
        
        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 20px rgba(102, 126, 234, 0.3);
        }
        
        .loading {
            display: none;
            text-align: center;
            padding: 40px;
        }
        
        .spinner {
            border: 4px solid #f3f3f3;
            border-top: 4px solid #667eea;
            border-radius: 50%;
            width: 50px;
            height: 50px;
            animation: spin 1s linear infinite;
            margin: 0 auto 20px;
        }
        
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        
        .results {
            display: none;
            padding: 40px;
            background: #f8f9ff;
        }
        
        .results h2 {
            color: #333;
            margin-bottom: 20px;
            font-size: 1.8em;
        }
        
        .feedback {
            background: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
            line-height: 1.6;
            white-space: pre-wrap;
        }
        
        .error {
            background: #fff5f5;
            color: #c53030;
            padding: 20px;
            border-radius: 10px;
            border-left: 4px solid #c53030;
            margin: 20px 0;
        }
        
        .success-msg {
            background: #f0fff4;
            color: #22543d;
            padding: 15px;
            border-radius: 10px;
            border-left: 4px solid #22543d;
            margin-bottom: 20px;
        }
        
        .new-analysis {
            text-align: center;
            margin-top: 30px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎯 AI Resume Analyzer</h1>
            <p>Get professional feedback on your resume powered by AI</p>
        </div>
        
        <div class="upload-section" id="uploadSection">
            <div class="dropzone" id="dropzone">
                <div class="upload-icon">📄</div>
                <div class="upload-text">Drag & drop your resume here</div>
                <div class="upload-subtext">or click to browse (PDF, DOCX supported)</div>
            </div>
            <input type="file" id="fileInput" accept=".pdf,.docx" />
            <button class="btn" onclick="document.getElementById('fileInput').click()">
                Choose File
            </button>
        </div>
        
        <div class="loading" id="loading">
            <div class="spinner"></div>
            <h3>Analyzing your resume...</h3>
            <p>Please wait while our AI reviews your resume</p>
        </div>
        
        <div class="results" id="results">
            <h2>📋 Analysis Results</h2>
            <div class="success-msg" id="successMsg"></div>
            <div class="feedback" id="feedback"></div>
            <div class="new-analysis">
                <button class="btn" onclick="resetAnalyzer()">Analyze Another Resume</button>
            </div>
        </div>
    </div>

    <script>
        const dropzone = document.getElementById('dropzone');
        const fileInput = document.getElementById('fileInput');
        const uploadSection = document.getElementById('uploadSection');
        const loading = document.getElementById('loading');
        const results = document.getElementById('results');
        const feedback = document.getElementById('feedback');
        const successMsg = document.getElementById('successMsg');

        // Drag and drop functionality
        dropzone.addEventListener('click', () => fileInput.click());
        
        dropzone.addEventListener('dragover', (e) => {
            e.preventDefault();
            dropzone.classList.add('dragover');
        });
        
        dropzone.addEventListener('dragleave', () => {
            dropzone.classList.remove('dragover');
        });
        
        dropzone.addEventListener('drop', (e) => {
            e.preventDefault();
            dropzone.classList.remove('dragover');
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                handleFile(files[0]);
            }
        });
        
        fileInput.addEventListener('change', (e) => {
            if (e.target.files.length > 0) {
                handleFile(e.target.files[0]);
            }
        });
        
        function handleFile(file) {
            // Validate file type
            const allowedTypes = ['application/pdf', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'];
            if (!allowedTypes.includes(file.type)) {
                showError('Please upload a PDF or DOCX file only.');
                return;
            }
            
            // Validate file size (16MB max)
            if (file.size > 16 * 1024 * 1024) {
                showError('File size must be less than 16MB.');
                return;
            }
            
            uploadFile(file);
        }
        
        function uploadFile(file) {
            const formData = new FormData();
            formData.append('resume', file);
            
            // Show loading state
            uploadSection.style.display = 'none';
            loading.style.display = 'block';
            results.style.display = 'none';
            
            fetch('/upload', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                loading.style.display = 'none';
                
                if (data.success) {
                    successMsg.textContent = `Analysis complete for: ${data.filename}`;
                    feedback.textContent = data.feedback;
                    results.style.display = 'block';
                } else {
                    showError(data.error || 'An error occurred while analyzing your resume.');
                    uploadSection.style.display = 'block';
                }
            })
            .catch(error => {
                loading.style.display = 'none';
                uploadSection.style.display = 'block';
                showError('Network error. Please check your connection and try again.');
                console.error('Error:', error);
            });
        }
        
        function showError(message) {
            const existingError = document.querySelector('.error');
            if (existingError) {
                existingError.remove();
            }
            
            const errorDiv = document.createElement('div');
            errorDiv.className = 'error';
            errorDiv.textContent = message;
            uploadSection.appendChild(errorDiv);
            
            setTimeout(() => {
                errorDiv.remove();
            }, 5000);
        }
        
        function resetAnalyzer() {
            uploadSection.style.display = 'block';
            loading.style.display = 'none';
            results.style.display = 'none';
            fileInput.value = '';
        }
    </script>
</body>
</html>
'''

if __name__ == '__main__':
    # Check if OpenAI API key is set
    if not os.getenv('OPENAI_API_KEY'):
        print("WARNING: OPENAI_API_KEY environment variable is not set!")
        print("Please set your OpenAI API key: export OPENAI_API_KEY='your-api-key-here'")
    
    app.run(debug=True, port=5000)