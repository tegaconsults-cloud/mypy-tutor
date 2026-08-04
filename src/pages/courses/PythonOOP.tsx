import React from 'react'
import CourseLandingPage from '../../components/CourseLandingPage'
import type { CourseLandingData } from '../../components/CourseLandingPage'

const data: CourseLandingData = {
  slug:'python-oop', title:'Object-Oriented Python', badge:'🏗️',
  tagline:'Classes, inheritance, polymorphism, and encapsulation.',
  description:'Object-Oriented Python — Classes, Inheritance, Polymorphism, Encapsulation. Build a full bank account class hierarchy as your capstone project.',
  level:'intermediate', category:'Intermediate Python', price_ngn:15000, xp_total:140, cert_level:'advanced',
  modules:[
    {step:1, title:'Python OOP Intro',      description:'What OOP is and why it matters.',                             type:'concept'},
    {step:2, title:'Classes and Objects',   description:'Creating classes and instantiating objects.',                 type:'concept'},
    {step:3, title:'__init__ Method',       description:'Constructors and instance variables.',                        type:'concept'},
    {step:4, title:'Self Parameter',        description:'How self references the instance.',                           type:'concept'},
    {step:5, title:'Class Properties',      description:'Instance and class attributes.',                              type:'concept'},
    {step:6, title:'Class Methods',         description:'Instance, class, and static methods.',                        type:'concept'},
    {step:7, title:'OOP Exercise',          description:'Build a complete class from scratch.',                        type:'exercise'},
    {step:8, title:'Python Inheritance',    description:'Subclasses and method overriding.',                           type:'concept'},
    {step:9, title:'Inheritance Exercise',  description:'Extend a base class.',                                        type:'exercise'},
    {step:10,title:'Python Polymorphism',   description:'Same interface, different implementations.',                  type:'concept'},
    {step:11,title:'Python Encapsulation',  description:'Private and protected attributes.',                           type:'concept'},
    {step:12,title:'Inner Classes',         description:'Classes defined inside other classes.',                       type:'concept'},
    {step:13,title:'OOP Quiz',              description:'Test your OOP knowledge.',                                    type:'quiz'},
    {step:14,title:'Capstone Project',      description:'Build a bank account class hierarchy.',                       type:'codegen'},
  ],
}
export default function PythonOOPPage() { return <CourseLandingPage data={data} /> }
