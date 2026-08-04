import React from 'react'
import CourseLandingPage from '../../components/CourseLandingPage'
import type { CourseLandingData } from '../../components/CourseLandingPage'

const data: CourseLandingData = {
  slug:'prompt-engineering', title:'Prompt Engineering', badge:'💬',
  tagline:'Write effective prompts for AI models — zero-shot, few-shot, chain-of-thought.',
  description:'Master prompt engineering — write effective prompts for AI models. Learn zero-shot, few-shot, and chain-of-thought prompting techniques.',
  level:'advanced', category:'AI & Prompting', price_ngn:30000, xp_total:100, cert_level:'executive',
  modules:[
    {step:1,title:'What is Prompt Engineering', description:'Introduction to prompting AI systems.',                  type:'concept'},
    {step:2,title:'Zero-shot Prompting',         description:'Getting results without examples.',                     type:'concept'},
    {step:3,title:'Few-shot Prompting',          description:'Using examples to guide AI output.',                    type:'concept'},
    {step:4,title:'Chain-of-thought Prompting',  description:'Step-by-step reasoning prompts.',                       type:'concept'},
    {step:5,title:'Prompt Exercise',             description:'Write prompts for real Python tasks.',                  type:'exercise'},
    {step:6,title:'Prompt Templates',            description:'Building reusable prompt structures.',                  type:'concept'},
    {step:7,title:'Role Prompting',              description:'Assigning roles to guide model behaviour.',              type:'concept'},
    {step:8,title:'Prompt Chaining',             description:'Linking prompts to build complex workflows.',           type:'concept'},
    {step:9,title:'Advanced Exercise',           description:'Build a prompt pipeline for a real project.',           type:'exercise'},
    {step:10,title:'Prompt Engineering Quiz',    description:'Test your prompting knowledge.',                        type:'quiz'},
  ],
}
export default function PromptEngineeringPage() { return <CourseLandingPage data={data} /> }
