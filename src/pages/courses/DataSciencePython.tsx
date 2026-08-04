import React from 'react'
import CourseLandingPage from '../../components/CourseLandingPage'
import type { CourseLandingData } from '../../components/CourseLandingPage'

const data: CourseLandingData = {
  slug:'data-science-python', title:'Data Science with Python', badge:'📊',
  tagline:'NumPy, Pandas, SciPy, and Matplotlib — the full data science stack.',
  description:'NumPy, Pandas, SciPy, and Matplotlib for data science and visualisation. Analyse a real dataset and visualise 3 insights as your capstone project.',
  level:'advanced', category:'Data Science', price_ngn:30000, xp_total:140, cert_level:'executive',
  modules:[
    {step:1, title:'NumPy Intro',              description:'Arrays, shapes, and operations.',                              type:'concept'},
    {step:2, title:'NumPy Exercise',           description:'Perform array operations.',                                    type:'exercise'},
    {step:3, title:'Pandas DataFrames',        description:'Create and analyse data with Pandas.',                         type:'concept'},
    {step:4, title:'Pandas Exercise',          description:'Filter, sort, and group data.',                                type:'exercise'},
    {step:5, title:'SciPy Basics',             description:'Scientific computing with SciPy.',                            type:'concept'},
    {step:6, title:'Matplotlib Pyplot',        description:'Basic plotting with pyplot.',                                  type:'concept'},
    {step:7, title:'Matplotlib Plotting',      description:'Line, markers, and labels.',                                   type:'concept'},
    {step:8, title:'Matplotlib Scatter',       description:'Scatter plots.',                                               type:'concept'},
    {step:9, title:'Matplotlib Bar Charts',    description:'Bar and horizontal bar charts.',                               type:'concept'},
    {step:10,title:'Matplotlib Histograms',    description:'Distribution visualisation.',                                  type:'concept'},
    {step:11,title:'Matplotlib Pie Charts',    description:'Pie and donut charts.',                                        type:'concept'},
    {step:12,title:'Matplotlib Subplots',      description:'Multiple plots in one figure.',                                type:'concept'},
    {step:13,title:'Data Science Quiz',        description:'Test your data science knowledge.',                            type:'quiz'},
    {step:14,title:'Capstone Project',         description:'Analyse a dataset and visualise 3 insights.',                  type:'codegen'},
  ],
}
export default function DataSciencePythonPage() { return <CourseLandingPage data={data} /> }
