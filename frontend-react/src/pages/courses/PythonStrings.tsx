import React from 'react'
import CourseLandingPage from '../../components/CourseLandingPage'
import type { CourseLandingData } from '../../components/CourseLandingPage'

const data: CourseLandingData = {
  slug:'python-strings', title:'Python Strings', badge:'📝',
  tagline:'Master every string method, f-strings, and text manipulation.',
  description:'Master Python strings — methods, formatting, slicing, and f-strings. Build real text-processing programs from scratch.',
  level:'beginner', category:'Python Basics', price_ngn:5000, xp_total:80, cert_level:'basic',
  modules:[
    {step:1,title:'Python Strings',             description:'Creating and accessing strings.',                         type:'concept'},
    {step:2,title:'String Slicing',             description:'Slice and index strings with [ : ].',                    type:'concept'},
    {step:3,title:'String Slicing Exercise',    description:'Practice slicing strings.',                              type:'exercise'},
    {step:4,title:'String Methods',             description:'upper, lower, strip, split, replace, find, count.',      type:'concept'},
    {step:5,title:'String Methods Exercise',    description:'Use the most common string methods.',                    type:'exercise'},
    {step:6,title:'String Formatting',          description:"f-strings, format(), and % formatting.",                 type:'concept'},
    {step:7,title:'String Formatting Exercise', description:'Build formatted output strings.',                        type:'exercise'},
    {step:8,title:'Strings Quiz',               description:'Test your string knowledge.',                            type:'quiz'},
  ],
}
export default function PythonStringsPage() { return <CourseLandingPage data={data} /> }
