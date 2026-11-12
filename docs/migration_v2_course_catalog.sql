-- =============================================================================
-- MyPyTutor 2.0 — Course Catalog Seed
-- =============================================================================
-- Populates course metadata for all 23 courses in the v2 curriculum.
-- Run AFTER migration_v2_monetisation.sql.
-- All INSERTs are idempotent via ON CONFLICT DO NOTHING.
-- course_slug must match course_prices.course_slug exactly.
-- =============================================================================

-- ---------------------------------------------------------------------------
-- course_catalog: full course metadata table
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS course_catalog (
    id                  UUID        DEFAULT gen_random_uuid() PRIMARY KEY,
    course_slug         VARCHAR(120) NOT NULL UNIQUE,
    title               VARCHAR(200) NOT NULL,
    subtitle            VARCHAR(300),
    description         TEXT,
    pillar              VARCHAR(60),   -- 'python', 'ai', 'ml'
    difficulty          VARCHAR(20),   -- 'beginner', 'intermediate', 'advanced'
    estimated_hours     INT,           -- approximate study time
    is_published        BOOLEAN     DEFAULT FALSE,
    is_free_preview     BOOLEAN     DEFAULT FALSE,
    prerequisites       TEXT[],        -- array of course slugs
    skills_covered      TEXT[],        -- key skills learner gains
    tools_covered       TEXT[],        -- libraries/tools used
    certificate_eligible BOOLEAN    DEFAULT TRUE,
    sort_order          INT         DEFAULT 0,
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    updated_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_course_catalog_pillar
    ON course_catalog (pillar, difficulty, sort_order);

-- ---------------------------------------------------------------------------
-- PILLAR 1 — Python Programming and Software Development
-- ---------------------------------------------------------------------------

INSERT INTO course_catalog (
    course_slug, title, subtitle, description, pillar, difficulty,
    estimated_hours, is_published, is_free_preview, prerequisites,
    skills_covered, tools_covered, certificate_eligible, sort_order
) VALUES (
    'python-fundamentals',
    'Python Fundamentals',
    'Start your Python journey from zero',
    'The complete beginner''s guide to Python programming. You will learn variables, data types, operators, conditions, loops, functions, modules, object-oriented programming, data structures, file handling and exception handling. By the end you will have the skills to build real Python programs from scratch.',
    'python', 'beginner', 25,
    TRUE, TRUE,
    ARRAY[]::TEXT[],
    ARRAY['Variables and data types', 'Conditions and loops', 'Functions and modules', 'OOP fundamentals', 'Data structures', 'File handling', 'Exception handling'],
    ARRAY['Python 3', 'VS Code', 'Jupyter Notebook'],
    TRUE, 10
),
(
    'advanced-python',
    'Advanced Python Programming',
    'Master Python at a professional level',
    'Take your Python skills beyond the basics. This course covers advanced language features, software engineering principles, design patterns, clean code practices, testing, debugging and performance optimisation. Ideal for developers who want to write production-quality Python.',
    'python', 'intermediate', 30,
    TRUE, FALSE,
    ARRAY['python-fundamentals'],
    ARRAY['Advanced OOP', 'Decorators and metaclasses', 'Generators and iterators', 'Design patterns', 'Testing with pytest', 'Debugging and profiling', 'Clean code principles'],
    ARRAY['Python 3', 'pytest', 'pylint', 'black'],
    TRUE, 20
),
(
    'python-web-dev',
    'Python for Web Development',
    'Build web applications and REST APIs with Python',
    'Learn to build modern web applications using Django, Flask and FastAPI. You will cover REST API development, authentication, authorisation, database integration, web scraping and deployment. Includes a full-stack project from design to live deployment.',
    'python', 'intermediate', 35,
    TRUE, FALSE,
    ARRAY['python-fundamentals'],
    ARRAY['Django', 'Flask', 'FastAPI', 'REST APIs', 'Authentication', 'Database integration', 'Deployment'],
    ARRAY['Django', 'Flask', 'FastAPI', 'PostgreSQL', 'SQLite', 'Heroku', 'Render'],
    TRUE, 30
),
(
    'python-automation',
    'Python for Automation',
    'Automate repetitive tasks and workflows with Python',
    'Eliminate repetitive work using Python automation. This course covers file and folder automation, Excel automation, email automation, browser automation with Selenium and Playwright, API automation, web scraping with BeautifulSoup and scheduled script execution.',
    'python', 'intermediate', 20,
    TRUE, FALSE,
    ARRAY['python-fundamentals'],
    ARRAY['File automation', 'Excel automation', 'Browser automation', 'Web scraping', 'API automation', 'Scheduled scripts'],
    ARRAY['Selenium', 'Playwright', 'BeautifulSoup', 'openpyxl', 'schedule'],
    TRUE, 40
),
(
    'python-data-analysis',
    'Python for Data Analysis',
    'Analyse real datasets with NumPy and Pandas',
    'Master data analysis using the most important Python data tools. You will work with NumPy arrays and Pandas DataFrames, clean and preprocess data, perform exploratory data analysis and create compelling visualisations. Includes real business datasets.',
    'python', 'intermediate', 30,
    TRUE, FALSE,
    ARRAY['python-fundamentals'],
    ARRAY['NumPy arrays', 'Pandas DataFrames', 'Data cleaning', 'EDA', 'Data visualisation', 'Statistical analysis'],
    ARRAY['NumPy', 'Pandas', 'Matplotlib', 'Seaborn', 'Jupyter Notebook'],
    TRUE, 50
),
(
    'python-cybersecurity',
    'Python for Cybersecurity',
    'Build security tools and automate cybersecurity tasks',
    'Apply Python to cybersecurity challenges. You will learn network programming, network scanning, log analysis, security automation, penetration-testing fundamentals, vulnerability assessment and security scripting. Ethical use only.',
    'python', 'advanced', 25,
    TRUE, FALSE,
    ARRAY['python-fundamentals', 'advanced-python'],
    ARRAY['Network programming', 'Security scanning', 'Log analysis', 'Security automation', 'Penetration testing basics', 'Vulnerability assessment'],
    ARRAY['socket', 'scapy', 'nmap', 'requests', 'paramiko'],
    TRUE, 60
),

-- ---------------------------------------------------------------------------
-- PILLAR 1 — Data Science
-- ---------------------------------------------------------------------------
(
    'data-science',
    'Data Science with Python',
    'From raw data to actionable insights',
    'A comprehensive data science course covering the full workflow: data collection, cleaning, preprocessing, exploratory analysis, statistical modelling, visualisation and storytelling. You will work with real-world datasets and build a data science portfolio project.',
    'python', 'intermediate', 40,
    TRUE, FALSE,
    ARRAY['python-fundamentals', 'python-data-analysis'],
    ARRAY['Data science workflow', 'Statistical analysis', 'Data storytelling', 'Business intelligence', 'Data visualisation', 'Predictive modelling basics'],
    ARRAY['Pandas', 'NumPy', 'Matplotlib', 'Seaborn', 'Plotly', 'Scikit-learn', 'Jupyter Notebook'],
    TRUE, 70
),

-- ---------------------------------------------------------------------------
-- PILLAR 2 — Artificial Intelligence
-- ---------------------------------------------------------------------------
(
    'ai-fundamentals',
    'AI Fundamentals',
    'Understand artificial intelligence from the ground up',
    'A clear and practical introduction to artificial intelligence. No programming required to begin. You will learn how AI works, its history, different types of AI systems, real-world applications, ethics, limitations and responsible use. Perfect for beginners and professionals entering the AI era.',
    'ai', 'beginner', 15,
    TRUE, TRUE,
    ARRAY[]::TEXT[],
    ARRAY['AI concepts', 'AI history', 'Types of AI', 'AI applications', 'AI ethics', 'Responsible AI', 'AI safety'],
    ARRAY[]::TEXT[],
    TRUE, 110
),
(
    'prompt-engineering',
    'Prompt Engineering',
    'Learn to communicate effectively with AI models',
    'Prompt engineering is the skill of writing instructions that get the best results from AI models. This course teaches you the anatomy of an effective prompt, zero-shot and few-shot techniques, chain-of-thought prompting, role-based prompting, structured prompting, multimodal prompting and advanced optimisation strategies.',
    'ai', 'beginner', 15,
    TRUE, TRUE,
    ARRAY[]::TEXT[],
    ARRAY['Prompt design', 'Zero-shot prompting', 'Few-shot prompting', 'Chain-of-thought', 'Role-based prompting', 'Prompt optimisation', 'Multimodal prompting'],
    ARRAY['ChatGPT', 'Claude', 'Gemini'],
    TRUE, 120
),
(
    'generative-ai',
    'Generative AI',
    'Create content, images and applications with AI',
    'Explore the technology behind modern AI content generation. You will learn about large language models, text generation, image generation, AI video and audio, multimodal AI, and how to apply generative AI to real business problems. Includes hands-on projects with leading AI platforms.',
    'ai', 'beginner', 20,
    TRUE, FALSE,
    ARRAY['ai-fundamentals'],
    ARRAY['LLMs', 'Text generation', 'Image generation', 'AI video and audio', 'Multimodal AI', 'Generative AI for business'],
    ARRAY['ChatGPT', 'DALL·E', 'Midjourney', 'Claude', 'Gemini', 'Sora'],
    TRUE, 130
),
(
    'ai-tools-productivity',
    'AI Tools and Productivity',
    'Use AI platforms to work faster and smarter',
    'Master the leading AI tools that are transforming professional productivity. You will learn ChatGPT, Claude, Google Gemini, Microsoft Copilot, Perplexity and NotebookLM. Covers AI for research, presentations, document creation, business administration, education and marketing.',
    'ai', 'beginner', 12,
    TRUE, TRUE,
    ARRAY[]::TEXT[],
    ARRAY['AI-powered research', 'AI writing assistance', 'AI presentations', 'Business AI', 'AI for education', 'AI for marketing'],
    ARRAY['ChatGPT', 'Claude', 'Gemini', 'Copilot', 'Perplexity', 'NotebookLM'],
    TRUE, 140
),
(
    'ai-app-development',
    'AI Application Development',
    'Build real AI-powered applications with Python',
    'Go from idea to working AI application. You will integrate OpenAI, Gemini and Claude APIs, build AI chatbots, conversational AI systems, AI-powered search, document processors and voice-enabled applications. Covers deployment, evaluation and responsible AI development.',
    'ai', 'intermediate', 35,
    TRUE, FALSE,
    ARRAY['ai-fundamentals', 'python-fundamentals'],
    ARRAY['API integration', 'Chatbot development', 'Conversational AI', 'AI-powered search', 'Document processing', 'Voice AI', 'AI deployment'],
    ARRAY['OpenAI API', 'Gemini API', 'Claude API', 'FastAPI', 'Python', 'Docker'],
    TRUE, 150
),
(
    'ai-agents-automation',
    'AI Agents and Automation',
    'Build autonomous AI agents and multi-agent systems',
    'The frontier of AI development. You will learn agent architecture, memory, planning, tool calling, multi-agent orchestration and autonomous workflows. Build intelligent agents using LangChain, LangGraph, CrewAI and AutoGen, and implement the Model Context Protocol (MCP).',
    'ai', 'advanced', 40,
    TRUE, FALSE,
    ARRAY['ai-app-development', 'python-fundamentals'],
    ARRAY['Agent architecture', 'Tool calling', 'Multi-agent systems', 'Autonomous workflows', 'RAG agents', 'Agent evaluation'],
    ARRAY['LangChain', 'LangGraph', 'CrewAI', 'AutoGen', 'MCP', 'Python'],
    TRUE, 160
),
(
    'rag-llm-development',
    'RAG and LLM Application Development',
    'Build intelligent knowledge-grounded AI applications',
    'Retrieval-Augmented Generation (RAG) enables AI applications to answer questions using your own documents and data. You will learn embeddings, vector databases, semantic search, document ingestion, chunking, indexing, retrieval, reranking and advanced RAG architectures. Includes complete application projects.',
    'ai', 'advanced', 35,
    TRUE, FALSE,
    ARRAY['ai-app-development'],
    ARRAY['RAG architecture', 'Embeddings', 'Vector databases', 'Semantic search', 'Document ingestion', 'Retrieval techniques', 'RAG evaluation'],
    ARRAY['LangChain', 'Chroma', 'Pinecone', 'Weaviate', 'OpenAI', 'Python'],
    TRUE, 170
),

-- ---------------------------------------------------------------------------
-- PILLAR 3 — Machine Learning
-- ---------------------------------------------------------------------------
(
    'ml-fundamentals',
    'Machine Learning Fundamentals',
    'Understand and apply machine learning from scratch',
    'A thorough introduction to machine learning. You will learn what ML is, how it differs from traditional programming, the main types of machine learning, mathematical foundations (linear algebra, probability, statistics, calculus), data preparation, feature engineering and model evaluation.',
    'ml', 'beginner', 30,
    TRUE, FALSE,
    ARRAY['python-fundamentals', 'python-data-analysis'],
    ARRAY['ML concepts', 'Mathematical foundations', 'Data preparation', 'Feature engineering', 'Model training', 'Model evaluation'],
    ARRAY['Scikit-learn', 'NumPy', 'Pandas', 'Jupyter Notebook'],
    TRUE, 210
),
(
    'supervised-ml',
    'Supervised Machine Learning',
    'Master algorithms that learn from labelled data',
    'Deep dive into supervised learning. You will implement and tune linear regression, logistic regression, decision trees, random forests, SVMs, KNN, Naive Bayes, gradient boosting, XGBoost, LightGBM and CatBoost. Covers classification, regression and practical model selection.',
    'ml', 'intermediate', 35,
    TRUE, FALSE,
    ARRAY['ml-fundamentals'],
    ARRAY['Linear regression', 'Logistic regression', 'Decision trees', 'Random forests', 'SVM', 'KNN', 'Gradient boosting', 'XGBoost'],
    ARRAY['Scikit-learn', 'XGBoost', 'LightGBM', 'CatBoost', 'Pandas'],
    TRUE, 220
),
(
    'unsupervised-ml',
    'Unsupervised Machine Learning',
    'Find patterns in data without labels',
    'Learn how to extract structure from unlabelled data. You will implement K-Means, hierarchical clustering, DBSCAN, Gaussian Mixture Models, PCA, dimensionality reduction, association rule learning and anomaly detection. Includes real business clustering and anomaly detection projects.',
    'ml', 'intermediate', 30,
    TRUE, FALSE,
    ARRAY['ml-fundamentals'],
    ARRAY['K-Means clustering', 'Hierarchical clustering', 'DBSCAN', 'PCA', 'Dimensionality reduction', 'Anomaly detection'],
    ARRAY['Scikit-learn', 'NumPy', 'Pandas', 'Matplotlib'],
    TRUE, 230
),
(
    'deep-learning',
    'Deep Learning',
    'Build and train neural networks with Python',
    'Master deep learning from fundamentals to advanced architectures. You will build feedforward networks, CNNs, RNNs, LSTMs, autoencoders, GANs and Transformer models. Covers backpropagation, activation functions, optimisers, transfer learning and fine-tuning on real datasets.',
    'ml', 'advanced', 45,
    TRUE, FALSE,
    ARRAY['ml-fundamentals', 'supervised-ml'],
    ARRAY['Neural networks', 'CNN', 'RNN', 'LSTM', 'Transformers', 'Transfer learning', 'GANs', 'Autoencoders'],
    ARRAY['TensorFlow', 'Keras', 'PyTorch', 'Hugging Face'],
    TRUE, 240
),
(
    'nlp',
    'Natural Language Processing',
    'Teach machines to understand human language',
    'Build applications that process, understand and generate human language. You will cover text preprocessing, tokenisation, text classification, sentiment analysis, named entity recognition, text summarisation, word embeddings, Transformer models for NLP, machine translation and chatbot development.',
    'ml', 'advanced', 40,
    TRUE, FALSE,
    ARRAY['deep-learning'],
    ARRAY['Text preprocessing', 'Text classification', 'Sentiment analysis', 'NER', 'Word embeddings', 'Transformers for NLP', 'Chatbot development'],
    ARRAY['NLTK', 'spaCy', 'Hugging Face', 'Transformers', 'TensorFlow', 'PyTorch'],
    TRUE, 250
),
(
    'computer-vision',
    'Computer Vision',
    'Teach machines to see and interpret images',
    'Build systems that can understand visual information. You will implement image classification, object detection, image segmentation, face detection, OCR, pose estimation and image generation. Covers CNN architectures, YOLO, OpenCV and Vision Transformers with practical projects.',
    'ml', 'advanced', 40,
    TRUE, FALSE,
    ARRAY['deep-learning'],
    ARRAY['Image classification', 'Object detection', 'Image segmentation', 'Face detection', 'OCR', 'CNN architectures', 'YOLO'],
    ARRAY['OpenCV', 'TensorFlow', 'PyTorch', 'YOLO', 'Keras'],
    TRUE, 260
),
(
    'reinforcement-learning',
    'Reinforcement Learning',
    'Train agents to make decisions through reward and feedback',
    'Learn how AI agents learn by interacting with environments. You will implement Q-Learning, Deep Q-Networks, policy gradients, Actor-Critic methods and Proximal Policy Optimisation. Covers Markov Decision Processes, multi-agent RL and practical projects in game environments.',
    'ml', 'advanced', 35,
    TRUE, FALSE,
    ARRAY['deep-learning', 'ml-fundamentals'],
    ARRAY['Q-Learning', 'DQN', 'Policy gradients', 'Actor-Critic', 'PPO', 'Multi-agent RL'],
    ARRAY['Gymnasium', 'Stable-Baselines3', 'PyTorch', 'TensorFlow'],
    TRUE, 270
),
(
    'mlops',
    'MLOps',
    'Deploy and manage machine learning systems in production',
    'Bridge the gap between ML development and production systems. You will learn ML lifecycle management, data versioning, experiment tracking, model deployment, serving, monitoring, drift detection, ML pipelines, feature stores, CI/CD for ML and cloud-based ML deployment.',
    'ml', 'advanced', 35,
    TRUE, FALSE,
    ARRAY['ml-fundamentals', 'supervised-ml'],
    ARRAY['ML lifecycle', 'Model deployment', 'Model monitoring', 'ML pipelines', 'CI/CD for ML', 'Feature stores', 'Model governance'],
    ARRAY['MLflow', 'DVC', 'Docker', 'Kubeflow', 'Weights & Biases', 'Scikit-learn'],
    TRUE, 280
),
(
    'advanced-ai-ml-engineering',
    'Advanced AI/ML Engineering',
    'Build production AI/ML systems end to end',
    'The capstone course for AI and ML engineers. You will design and build complete production AI systems combining deep learning, NLP, computer vision, MLOps, LLMs, agents and deployment. Covers system design, scalability, model governance, responsible AI and career preparation.',
    'ml', 'advanced', 50,
    TRUE, FALSE,
    ARRAY['deep-learning', 'nlp', 'mlops', 'ai-agents-automation'],
    ARRAY['Production ML systems', 'AI system design', 'Model governance', 'Responsible AI', 'Scalable deployment', 'Portfolio development'],
    ARRAY['TensorFlow', 'PyTorch', 'LangChain', 'MLflow', 'Docker', 'AWS', 'Hugging Face'],
    TRUE, 290
)
ON CONFLICT (course_slug) DO NOTHING;

-- ---------------------------------------------------------------------------
-- Update course_prices to reference new course_catalog where not yet set
-- (safe to run — only sets is_active = TRUE for courses that exist in catalog)
-- ---------------------------------------------------------------------------
UPDATE course_prices
SET is_active = TRUE
WHERE course_slug IN (SELECT course_slug FROM course_catalog)
  AND is_active = FALSE;
