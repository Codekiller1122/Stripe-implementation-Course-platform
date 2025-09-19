import React, {useEffect, useState} from 'react';
import axios from 'axios';
export default function Dashboard(){
  const [courses,setCourses]=useState([]);
  useEffect(()=>{ fetch(); },[]);
  async function fetch(){ const res = await axios.get('/api/courses/').catch(()=>({data:[]})); setCourses(res.data || []); }
  async function buy(course){
    const email = prompt('Enter your email for receipt:');
    if(!email) return;
    const res = await axios.post('/api/payments/create-checkout-session/', {course_id: course.id, email}).catch(e=>{ alert('Failed to create checkout session'); console.error(e); });
    if(res && res.data && res.data.url){
      window.location.href = res.data.url;
    } else if(res && res.data && res.data.id){
      // if stripe returns session id only, redirect via stripe.checkout
      window.location.href = 'https://checkout.stripe.com/pay/' + res.data.id;
    }
  }
  return (<div>
    <h2>Courses</h2>
    <table border='1' cellPadding='8'><thead><tr><th>Title</th><th>Instructor</th><th>Price</th><th>Action</th></tr></thead><tbody>{courses.map(c=>(<tr key={c.id}><td>{c.title}</td><td>{c.instructor_name}</td><td>${(c.price_cents/100).toFixed(2)}</td><td>{c.price_cents>0? <><button onClick={()=>buy(c)}>Buy</button> <button onClick={()=>paypalDonate(c)}>PayPal</button> <button onClick={()=>paypalSubscribe(c)}>PayPal Sub</button></> : 'Free'}</td></tr>))}</tbody></table>
    <p>Tip: This demo uses Stripe Checkout for payments. For subscriptions, use the subscription flow.</p>
  </div>);
}
