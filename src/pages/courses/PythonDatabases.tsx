import React from 'react'
import CourseLandingPage from '../../components/CourseLandingPage'
import type { CourseLandingData } from '../../components/CourseLandingPage'

const data: CourseLandingData = {
  slug:'python-databases', title:'Python with Databases', badge:'🗄️',
  tagline:'MySQL and MongoDB — full database integration in Python.',
  description:'Python with MySQL and MongoDB — full CRUD database integration. Build a Python REST API backed by MySQL as your capstone project.',
  level:'advanced', category:'Advanced Python', price_ngn:30000, xp_total:140, cert_level:'executive',
  modules:[
    {step:1, title:'MySQL Get Started',    description:'Connect Python to MySQL with mysql-connector.',           type:'concept'},
    {step:2, title:'MySQL Create Database',description:'Create a database from Python.',                         type:'codegen'},
    {step:3, title:'MySQL Create Table',   description:'Define tables with Python.',                             type:'codegen'},
    {step:4, title:'MySQL Insert',         description:'Insert rows with parameterised queries.',                type:'concept'},
    {step:5, title:'MySQL Select',         description:'Fetch and display records.',                             type:'concept'},
    {step:6, title:'MySQL Where & Order',  description:'Filter and sort results.',                               type:'concept'},
    {step:7, title:'MySQL Update & Delete',description:'Modify and remove records.',                             type:'concept'},
    {step:8, title:'MySQL Join',           description:'Join tables in queries.',                                type:'concept'},
    {step:9, title:'MySQL Exercise',       description:'Build a CRUD app with MySQL.',                           type:'exercise'},
    {step:10,title:'MongoDB Get Started',  description:'Connect Python to MongoDB with pymongo.',               type:'concept'},
    {step:11,title:'MongoDB CRUD',         description:'Insert, find, query, update, delete.',                   type:'concept'},
    {step:12,title:'MongoDB Exercise',     description:'Build a document-based data store.',                     type:'exercise'},
    {step:13,title:'Databases Quiz',       description:'Test your database knowledge.',                          type:'quiz'},
    {step:14,title:'Capstone Project',     description:'Build a Python REST API backed by MySQL.',              type:'codegen'},
  ],
}
export default function PythonDatabasesPage() { return <CourseLandingPage data={data} /> }
