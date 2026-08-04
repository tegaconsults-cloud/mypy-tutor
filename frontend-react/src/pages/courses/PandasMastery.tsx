import React from 'react'
import CourseLandingPage from '../../components/CourseLandingPage'
import type { CourseLandingData } from '../../components/CourseLandingPage'

const data: CourseLandingData = {
  slug:'pandas-mastery', title:'Pandas Mastery', badge:'🐼',
  tagline:'Series, DataFrames, CSV/JSON, data cleaning, analysis, and plotting.',
  description:'Complete Pandas — Series, DataFrames, CSV/JSON, data cleaning, analysis, and plotting. Perform end-to-end EDA on a real dataset as your capstone project.',
  level:'advanced', category:'Data Science', price_ngn:30000, xp_total:150, cert_level:'executive',
  modules:[
    {step:1, title:'Pandas Intro & Getting Started',  description:'What Pandas is, Series vs DataFrame, installation.',                  type:'concept'},
    {step:2, title:'Pandas Series',                   description:'Creating Series from lists, dicts, scalars; index, values, dtype.',    type:'concept'},
    {step:3, title:'Pandas DataFrames',               description:'Creating DataFrames, loc, iloc, accessing columns and rows.',          type:'concept'},
    {step:4, title:'DataFrame Exercise',              description:'Build and query a multi-column DataFrame.',                             type:'exercise'},
    {step:5, title:'Read CSV & JSON',                 description:'pd.read_csv(), pd.read_json(), head(), tail(), info().',               type:'concept'},
    {step:6, title:'Analyzing Data',                  description:'describe(), mean(), median(), mode(), std(), count(), value_counts().', type:'concept'},
    {step:7, title:'Data Analysis Exercise',          description:'Analyze a sample sales dataset and extract insights.',                 type:'exercise'},
    {step:8, title:'Cleaning Empty Cells',            description:'dropna(), fillna(), interpolate(), isnull(), notnull().',              type:'concept'},
    {step:9, title:'Cleaning Wrong Format & Data',    description:'to_datetime(), astype(), str methods, apply(), replace().',           type:'concept'},
    {step:10,title:'Removing Duplicates',             description:'duplicated(), drop_duplicates(), reset_index().',                      type:'concept'},
    {step:11,title:'Data Cleaning Exercise',          description:'Clean a messy real-world dataset from scratch.',                       type:'exercise'},
    {step:12,title:'Pandas Correlations',             description:'corr(), corrwith(), heatmap interpretation, feature relationships.',   type:'concept'},
    {step:13,title:'Pandas Plotting',                 description:'df.plot(), line, bar, hist, scatter, pie — matplotlib integration.',   type:'concept'},
    {step:14,title:'Pandas Quiz',                     description:'Test your full Pandas knowledge.',                                     type:'quiz'},
    {step:15,title:'Capstone Project',                description:'End-to-end EDA: load, clean, analyse, and visualise a real dataset.', type:'codegen'},
  ],
}
export default function PandasMasteryPage() { return <CourseLandingPage data={data} /> }
