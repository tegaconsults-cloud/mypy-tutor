import React from 'react'
import CourseLandingPage from '../../components/CourseLandingPage'
import type { CourseLandingData } from '../../components/CourseLandingPage'

const data: CourseLandingData = {
  slug:'numpy-mastery', title:'NumPy Mastery', badge:'🔢',
  tagline:'Complete NumPy — arrays, indexing, random, ufuncs, and statistical distributions.',
  description:'Complete NumPy — arrays, indexing, random, ufuncs, and statistical distributions. Build a statistical analysis tool as your capstone project.',
  level:'advanced', category:'Data Science', price_ngn:30000, xp_total:160, cert_level:'executive',
  modules:[
    {step:1, title:'NumPy Intro & Getting Started',    description:'What NumPy is, why faster than lists, how to install.',          type:'concept'},
    {step:2, title:'Creating Arrays',                  description:'np.array(), np.zeros(), np.ones(), np.arange(), np.linspace().',  type:'concept'},
    {step:3, title:'Array Indexing & Slicing',         description:'1D, 2D, 3D indexing, negative indexing, and slice syntax.',      type:'concept'},
    {step:4, title:'Indexing Exercise',                description:'Practice array indexing and slicing on 2D and 3D arrays.',       type:'exercise'},
    {step:5, title:'Array Shape & Reshape',            description:'ndim, shape, size, reshape(), flatten(), ravel().',              type:'concept'},
    {step:6, title:'NumPy Data Types',                 description:'dtypes, astype(), copy vs view.',                                type:'concept'},
    {step:7, title:'Array Iterating',                  description:'Iterating with nditer(), ndenumerate(), and broadcasting.',      type:'concept'},
    {step:8, title:'Join, Split, Search, Sort, Filter',description:'concatenate(), stack(), split(), where(), sort(), filter.',      type:'concept'},
    {step:9, title:'NumPy Operations Exercise',        description:'Build a data pipeline using array operations.',                  type:'exercise'},
    {step:10,title:'NumPy Random — Distributions',    description:'Normal, Binomial, Poisson, Uniform, Exponential, Chi-Square.',   type:'concept'},
    {step:11,title:'Random Exercise',                  description:'Simulate real-world data using NumPy random distributions.',     type:'exercise'},
    {step:12,title:'ufunc Intro & Arithmetic',         description:'Universal functions, frompyfunc(), add, subtract, multiply.',    type:'concept'},
    {step:13,title:'ufunc Math Operations',            description:'Logs, rounding, summation, products, differences, LCM, GCD.',    type:'concept'},
    {step:14,title:'ufunc Trig & Set Operations',      description:'sin, cos, tan, arcsin, hyperbolic, union, intersect, setdiff.', type:'concept'},
    {step:15,title:'NumPy Quiz',                       description:'Test your full NumPy knowledge.',                                type:'quiz'},
    {step:16,title:'Capstone Project',                 description:'Build a statistical analysis tool using NumPy arrays and ufuncs.',type:'codegen'},
  ],
}
export default function NumpyMasteryPage() { return <CourseLandingPage data={data} /> }
