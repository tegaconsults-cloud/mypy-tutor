import React from 'react'
import CourseLandingPage from '../../components/CourseLandingPage'
import type { CourseLandingData } from '../../components/CourseLandingPage'

const data: CourseLandingData = {
  slug:'machine-learning', title:'Machine Learning with Python', badge:'🤖',
  tagline:'30 lessons — supervised, unsupervised, and deep learning in Python.',
  description:'Comprehensive machine learning with Python — from regression to neural networks. Build real ML models using scikit-learn, TensorFlow, and Keras.',
  level:'advanced', category:'Machine Learning', price_ngn:50000, xp_total:300, cert_level:'executive',
  modules:[
    {step:1, title:'What is Machine Learning',      description:'Supervised, unsupervised, and reinforcement learning.',           type:'concept'},
    {step:2, title:'ML Workflow',                   description:'Data → Model → Train → Evaluate → Deploy.',                      type:'concept'},
    {step:3, title:'Data Preprocessing',            description:'Cleaning, normalisation, encoding, and splitting datasets.',      type:'concept'},
    {step:4, title:'Data Preprocessing Exercise',   description:'Clean and prepare a real-world dataset.',                        type:'exercise'},
    {step:5, title:'Linear Regression',             description:'Predict continuous values with linear models.',                   type:'concept'},
    {step:6, title:'Linear Regression Exercise',    description:'Build a house price prediction model.',                          type:'exercise'},
    {step:7, title:'Logistic Regression',           description:'Binary and multiclass classification.',                          type:'concept'},
    {step:8, title:'Decision Trees',                description:'Tree-based models for classification and regression.',           type:'concept'},
    {step:9, title:'Random Forest',                 description:'Ensemble learning with multiple decision trees.',                type:'concept'},
    {step:10,title:'Classification Exercise',       description:'Build a spam email classifier.',                                 type:'exercise'},
    {step:11,title:'Support Vector Machines',       description:'Kernel trick and SVM for complex classification.',               type:'concept'},
    {step:12,title:'K-Nearest Neighbours',          description:'Distance-based classification algorithm.',                       type:'concept'},
    {step:13,title:'Naive Bayes',                   description:'Probabilistic classifier for text and data.',                    type:'concept'},
    {step:14,title:'Model Evaluation',              description:'Accuracy, precision, recall, F1, ROC-AUC.',                      type:'concept'},
    {step:15,title:'Cross-validation & Tuning',     description:'GridSearchCV, RandomizedSearchCV, hyperparameter tuning.',       type:'concept'},
    {step:16,title:'Clustering — K-Means',          description:'Unsupervised learning and customer segmentation.',               type:'concept'},
    {step:17,title:'Dimensionality Reduction',      description:'PCA and t-SNE for high-dimensional data.',                      type:'concept'},
    {step:18,title:'Unsupervised Exercise',         description:'Cluster a customer dataset and visualise segments.',             type:'exercise'},
    {step:19,title:'Neural Networks — Intro',       description:'Perceptrons, layers, activation functions.',                     type:'concept'},
    {step:20,title:'Deep Learning with Keras',      description:'Build and train a neural network in Python.',                    type:'concept'},
    {step:21,title:'Convolutional Neural Networks', description:'CNNs for image classification.',                                 type:'concept'},
    {step:22,title:'Recurrent Neural Networks',     description:'RNNs and LSTMs for sequence data.',                              type:'concept'},
    {step:23,title:'Transfer Learning',             description:'Fine-tuning pre-trained models (ResNet, BERT).',                 type:'concept'},
    {step:24,title:'Deep Learning Exercise',        description:'Train a CNN on the MNIST digit dataset.',                        type:'exercise'},
    {step:25,title:'Natural Language Processing',   description:'Text vectorisation, sentiment analysis, TF-IDF.',               type:'concept'},
    {step:26,title:'NLP Exercise',                  description:'Build a sentiment analyser for product reviews.',                type:'exercise'},
    {step:27,title:'ML Project Pipeline',           description:'End-to-end ML project: data → model → API endpoint.',          type:'concept'},
    {step:28,title:'Model Deployment',              description:'Saving models with joblib/pickle, serving with FastAPI.',        type:'concept'},
    {step:29,title:'Machine Learning Quiz',         description:'Comprehensive ML knowledge assessment.',                         type:'quiz'},
    {step:30,title:'Capstone Project',              description:'Build, evaluate, and deploy a full ML classification model.',   type:'codegen'},
  ],
}
export default function MachineLearningPage() { return <CourseLandingPage data={data} /> }
