import React from 'react'
import CourseLandingPage from '../../components/CourseLandingPage'
import type { CourseLandingData } from '../../components/CourseLandingPage'

const data: CourseLandingData = {
  slug:'python-modules-stdlib', title:'Modules & Standard Library', badge:'📚',
  tagline:'Dates, Math, JSON, RegEx, file handling, and virtual environments.',
  description:'Python standard library — Dates, Math, JSON, RegEx, PIP, File Handling. Build a file-based note manager as your exercise.',
  level:'intermediate', category:'Intermediate Python', price_ngn:15000, xp_total:150, cert_level:'advanced',
  modules:[
    {step:1, title:'Python Modules',            description:'Creating, importing, and using modules.',                      type:'concept'},
    {step:2, title:'Python Dates',              description:'datetime module — dates, times, and formatting.',              type:'concept'},
    {step:3, title:'Dates Exercise',            description:'Format and calculate dates.',                                  type:'exercise'},
    {step:4, title:'Python Math',               description:'math module — functions and constants.',                       type:'concept'},
    {step:5, title:'Python JSON',               description:'Parsing and generating JSON data.',                            type:'concept'},
    {step:6, title:'JSON Exercise',             description:'Serialize and deserialize data structures.',                   type:'exercise'},
    {step:7, title:'Python RegEx',              description:'Pattern matching with the re module.',                         type:'concept'},
    {step:8, title:'RegEx Exercise',            description:'Write regex patterns for real tasks.',                         type:'exercise'},
    {step:9, title:'Python PIP',                description:'Installing and managing packages.',                            type:'concept'},
    {step:10,title:'Virtual Environments',      description:'Creating isolated Python environments.',                       type:'concept'},
    {step:11,title:'Try Except',                description:'Handling errors with try/except/finally.',                     type:'concept'},
    {step:12,title:'Custom Exceptions',         description:'Defining your own exception classes.',                         type:'concept'},
    {step:13,title:'File Handling',             description:'Opening, reading, writing, and deleting files.',               type:'concept'},
    {step:14,title:'File Handling Exercise',    description:'Build a file-based note manager.',                             type:'exercise'},
    {step:15,title:'Modules Quiz',              description:'Test your standard library knowledge.',                        type:'quiz'},
  ],
}
export default function PythonModulesStdlibPage() { return <CourseLandingPage data={data} /> }
