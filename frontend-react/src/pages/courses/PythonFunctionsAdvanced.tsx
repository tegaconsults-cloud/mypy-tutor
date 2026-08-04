import React from 'react'
import CourseLandingPage from '../../components/CourseLandingPage'
import type { CourseLandingData } from '../../components/CourseLandingPage'

const data: CourseLandingData = {
  slug:'python-functions-advanced', title:'Functions & Advanced Python', badge:'⚡',
  tagline:'Decorators, closures, generators, and the full function toolkit.',
  description:'Functions, Lambda, Scope, Closures, Decorators, Iterators, and Generators. Build a data pipeline using generators and decorators as your capstone.',
  level:'intermediate', category:'Intermediate Python', price_ngn:15000, xp_total:140, cert_level:'advanced',
  modules:[
    {step:1, title:'Python Functions',          description:'Defining, calling, and returning from functions.',              type:'concept'},
    {step:2, title:'Function Arguments',        description:'Positional, keyword, *args, and **kwargs.',                    type:'concept'},
    {step:3, title:'Arguments Exercise',        description:'Write flexible functions with *args/**kwargs.',                type:'exercise'},
    {step:4, title:'Lambda Functions',          description:'Anonymous one-line functions.',                                type:'concept'},
    {step:5, title:'Python Scope',              description:'Local, global, and nonlocal scope.',                           type:'concept'},
    {step:6, title:'Python Recursion',          description:'Functions that call themselves.',                              type:'concept'},
    {step:7, title:'Python Closures',           description:'Functions that capture their environment.',                    type:'concept'},
    {step:8, title:'Python Decorators',         description:'Wrapping functions with @decorator syntax.',                   type:'concept'},
    {step:9, title:'Decorators Exercise',       description:'Write and apply a custom decorator.',                          type:'exercise'},
    {step:10,title:'Python Arrays',             description:'Using arrays vs lists in Python.',                             type:'concept'},
    {step:11,title:'Python Iterators',          description:'__iter__ and __next__ explained.',                             type:'concept'},
    {step:12,title:'Python Generators',         description:'yield and lazy evaluation.',                                   type:'concept'},
    {step:13,title:'Advanced Functions Quiz',   description:'Test your advanced functions knowledge.',                      type:'quiz'},
    {step:14,title:'Capstone Project',          description:'Build a data pipeline using generators and decorators.',       type:'codegen'},
  ],
}
export default function PythonFunctionsAdvancedPage() { return <CourseLandingPage data={data} /> }
