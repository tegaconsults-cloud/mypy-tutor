import React from 'react'
import CourseLandingPage from '../../components/CourseLandingPage'
import type { CourseLandingData } from '../../components/CourseLandingPage'

const data: CourseLandingData = {
  slug:'python-dsa', title:'Data Structures & Algorithms', badge:'🧠',
  tagline:'Stacks, queues, trees, graphs, sorting and searching algorithms.',
  description:'DSA from W3Schools — fully in Python. Covers all major data structures and algorithms. Build a graph BFS/DFS pathfinder as your capstone project.',
  level:'advanced', category:'Advanced Python', price_ngn:30000, xp_total:210, cert_level:'executive',
  modules:[
    {step:1, title:'DSA Intro',                  description:'What DSA is and why it matters.',                            type:'concept'},
    {step:2, title:'Lists and Arrays',           description:'Arrays vs lists, time complexity.',                          type:'concept'},
    {step:3, title:'Stacks',                     description:'LIFO structure with push/pop.',                              type:'concept'},
    {step:4, title:'Queues',                     description:'FIFO structure with enqueue/dequeue.',                       type:'concept'},
    {step:5, title:'Linked Lists',               description:'Singly and doubly linked lists.',                            type:'concept'},
    {step:6, title:'Hash Tables',                description:'Key-value storage with hashing.',                            type:'concept'},
    {step:7, title:'Trees',                      description:'Tree structure, nodes, and traversal.',                      type:'concept'},
    {step:8, title:'Binary Trees',               description:'Binary tree operations.',                                    type:'concept'},
    {step:9, title:'Binary Search Trees',        description:'BST insert, search, delete.',                                type:'concept'},
    {step:10,title:'AVL Trees',                  description:'Self-balancing BST.',                                        type:'concept'},
    {step:11,title:'Graphs',                     description:'Graph representation, BFS, DFS.',                            type:'concept'},
    {step:12,title:'Linear Search',              description:'Sequential search algorithm.',                               type:'concept'},
    {step:13,title:'Binary Search',              description:'Divide-and-conquer search.',                                 type:'concept'},
    {step:14,title:'Bubble Sort',                description:'Simple comparison-based sort.',                              type:'concept'},
    {step:15,title:'Selection Sort',             description:'Find minimum and place.',                                    type:'concept'},
    {step:16,title:'Insertion Sort',             description:'Build sorted array one item at a time.',                     type:'concept'},
    {step:17,title:'Quick Sort',                 description:'Partition-based recursive sort.',                            type:'concept'},
    {step:18,title:'Merge Sort',                 description:'Divide, sort, and merge.',                                   type:'concept'},
    {step:19,title:'Counting & Radix Sort',      description:'Non-comparison sorting algorithms.',                         type:'concept'},
    {step:20,title:'DSA Quiz',                   description:'Test your DSA knowledge.',                                   type:'quiz'},
    {step:21,title:'Capstone Project',           description:'Implement a graph BFS/DFS pathfinder in Python.',           type:'codegen'},
  ],
}
export default function PythonDSAPage() { return <CourseLandingPage data={data} /> }
