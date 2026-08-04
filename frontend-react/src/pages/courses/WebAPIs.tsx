import React from 'react'
import CourseLandingPage from '../../components/CourseLandingPage'
import type { CourseLandingData } from '../../components/CourseLandingPage'

const data: CourseLandingData = {
  slug:'web-apis', title:'Web APIs — FastAPI & Flask', badge:'🌐',
  tagline:'Build and consume REST APIs with FastAPI, Flask, and Django.',
  description:'Build and consume REST APIs with FastAPI and the requests library. Build a documented REST API with FastAPI as your capstone project.',
  level:'advanced', category:'Advanced Python', price_ngn:30000, xp_total:90, cert_level:'executive',
  modules:[
    {step:1,title:'HTTP & REST Basics',  description:'How the web works.',                              type:'concept'},
    {step:2,title:'Requests Module',     description:'Fetch data from a public API.',                   type:'codegen'},
    {step:3,title:'FastAPI Intro',       description:'Build your first FastAPI endpoint.',              type:'concept'},
    {step:4,title:'FastAPI Exercise',    description:'Add a new route to a FastAPI app.',               type:'exercise'},
    {step:5,title:'Flask Basics',        description:'Build a web app with Flask.',                     type:'concept'},
    {step:6,title:'Flask Exercise',      description:'Add routes to a Flask app.',                      type:'exercise'},
    {step:7,title:'Django Overview',     description:'Introduction to Django for web development.',     type:'concept'},
    {step:8,title:'APIs Quiz',           description:'Test your API knowledge.',                        type:'quiz'},
    {step:9,title:'Capstone Project',    description:'Build a documented REST API with FastAPI.',       type:'codegen'},
  ],
}
export default function WebAPIsPage() { return <CourseLandingPage data={data} /> }
