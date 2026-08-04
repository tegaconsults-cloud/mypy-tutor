import React from 'react'
import CourseLandingPage from '../../components/CourseLandingPage'
import type { CourseLandingData } from '../../components/CourseLandingPage'

const data: CourseLandingData = {
  slug:'python-control-flow', title:'Python Control Flow', badge:'🔀',
  tagline:'If/Else, loops, range, break and continue — take full control.',
  description:'If/Else, Match, While, For, Range, Break, Continue — full Python control flow. Build a number guessing game as your capstone project.',
  level:'beginner', category:'Python Basics', price_ngn:5000, xp_total:100, cert_level:'basic',
  modules:[
    {step:1, title:'If...Else',              description:'Conditional statements with if, elif, else.',              type:'concept'},
    {step:2, title:'Match Statement',        description:'Python 3.10+ structural pattern matching.',               type:'concept'},
    {step:3, title:'While Loops',            description:'Repeating code while a condition is true.',               type:'concept'},
    {step:4, title:'For Loops',              description:'Iterating over sequences with for.',                      type:'concept'},
    {step:5, title:'Python Range',           description:'Generating number sequences with range().',               type:'concept'},
    {step:6, title:'Break and Continue',     description:'Controlling loop flow with break and continue.',          type:'concept'},
    {step:7, title:'Pass Statement',         description:'Using pass as a placeholder.',                           type:'concept'},
    {step:8, title:'Control Flow Exercise',  description:'Write programs using loops and conditionals.',           type:'exercise'},
    {step:9, title:'Control Flow Quiz',      description:'Test your control flow knowledge.',                      type:'quiz'},
    {step:10,title:'Capstone Project',       description:'Build a number guessing game.',                          type:'codegen'},
  ],
}
export default function PythonControlFlowPage() { return <CourseLandingPage data={data} /> }
