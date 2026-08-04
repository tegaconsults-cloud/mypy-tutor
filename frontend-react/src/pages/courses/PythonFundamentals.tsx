import React from 'react'
import CourseLandingPage from '../../components/CourseLandingPage'
import type { CourseLandingData } from '../../components/CourseLandingPage'

const data: CourseLandingData = {
  slug: 'python-fundamentals', title: 'Python Fundamentals', badge: '🐍',
  tagline: 'Start your Python journey from absolute zero.',
  description: 'Master Python from zero — syntax, variables, data types, operators, and output. No prior experience needed. Sir. Tega explains every concept clearly with real-world examples.',
  level: 'beginner', category: 'Python Basics', price_ngn: 5000, xp_total: 140, cert_level: 'basic',
  modules: [
    { step:1,  title:'Python Intro & Get Started', description:'What Python is and how to install it.',                            type:'concept'  },
    { step:2,  title:'Python Syntax',              description:'Indentation, statements, and structure.',                          type:'concept'  },
    { step:3,  title:'Python Output',              description:'Using print() and output formatting.',                             type:'concept'  },
    { step:4,  title:'Python Comments',            description:'Single-line and multi-line comments.',                             type:'concept'  },
    { step:5,  title:'Python Variables',           description:'Declaring, assigning, and naming variables.',                      type:'concept'  },
    { step:6,  title:'Variables Exercise',         description:'Practice declaring and using variables.',                          type:'exercise' },
    { step:7,  title:'Python Data Types',          description:'int, float, str, bool, list, dict, etc.',                         type:'concept'  },
    { step:8,  title:'Python Numbers',             description:'Integers, floats, and complex numbers.',                           type:'concept'  },
    { step:9,  title:'Python Casting',             description:"Converting between types with int(), str(), float().",             type:'concept'  },
    { step:10, title:'Python Booleans',            description:'True, False, and boolean logic.',                                  type:'concept'  },
    { step:11, title:'Python Operators',           description:'Arithmetic, comparison, logical, and assignment operators.',       type:'concept'  },
    { step:12, title:'Operators Exercise',         description:'Solve problems using Python operators.',                           type:'exercise' },
    { step:13, title:'Basics Quiz',                description:'Test your Python basics knowledge.',                               type:'quiz'     },
    { step:14, title:'Capstone Project',           description:'Build a simple calculator using variables and operators.',         type:'codegen'  },
  ],
}
export default function PythonFundamentalsPage() { return <CourseLandingPage data={data} /> }
