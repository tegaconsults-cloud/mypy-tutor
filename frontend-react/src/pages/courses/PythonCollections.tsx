import React from 'react'
import CourseLandingPage from '../../components/CourseLandingPage'
import type { CourseLandingData } from '../../components/CourseLandingPage'

const data: CourseLandingData = {
  slug:'python-collections', title:'Python Collections', badge:'📦',
  tagline:'Lists, Tuples, Sets and Dictionaries — Python\'s four core containers.',
  description:'Python Lists, Tuples, Sets, and Dictionaries — the four core collection types. Build a student grade tracker as your capstone project.',
  level:'beginner', category:'Python Basics', price_ngn:5000, xp_total:110, cert_level:'basic',
  modules:[
    {step:1, title:'Python Lists',          description:'Creating, accessing, and modifying lists.',                   type:'concept'},
    {step:2, title:'List Methods',          description:'append, remove, sort, pop, insert and more.',                type:'concept'},
    {step:3, title:'List Comprehension',    description:'Create lists with one-line expressions.',                    type:'concept'},
    {step:4, title:'Lists Exercise',        description:'Manipulate lists with methods and comprehensions.',          type:'exercise'},
    {step:5, title:'Python Tuples',         description:'Immutable sequences and tuple methods.',                     type:'concept'},
    {step:6, title:'Python Sets',           description:'Unordered unique collections and set methods.',              type:'concept'},
    {step:7, title:'Python Dictionaries',   description:'Key-value storage and dictionary methods.',                  type:'concept'},
    {step:8, title:'Dictionary Methods',    description:'keys, values, items, get, update and more.',                 type:'concept'},
    {step:9, title:'Collections Exercise',  description:'Build a word frequency counter using a dictionary.',         type:'exercise'},
    {step:10,title:'Collections Quiz',      description:'Test your knowledge of Python collections.',                 type:'quiz'},
    {step:11,title:'Capstone Project',      description:'Build a student grade tracker using lists and dicts.',       type:'codegen'},
  ],
}
export default function PythonCollectionsPage() { return <CourseLandingPage data={data} /> }
