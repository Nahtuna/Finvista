# 🎥 How Machines Learn: Gradient Descent, Stochastic Gradient Descent, Simulated Annealing

> **Nguồn tri thức tự động từ YouTube** | Kênh: [Roman Paolucci](https://www.youtube.com/@QuantGuild)

## 📊 1. THÔNG TIN THAM CHIẾU
| Thuộc tính | Giá trị |
|---|---|
| **Đường dẫn (URL)** | [Xem trên YouTube](https://www.youtube.com/watch?v=0SX_GAgMNkA) |
| **Video ID** | `0SX_GAgMNkA` |
| **Thời lượng** | `23:24` |
| **Ngày tải lên** | `2024-06-15` |
| **Ngôn ngữ Transcript** | `CỤC BỘ (CACHED)` |

## 🛠️ 3. TÀI NGUYÊN & MÃ NGUỒN LIÊN KẾT

### 🔗 Tài liệu và liên kết khác:
- [https://medium.com/quant-guild](https://medium.com/quant-guild)
- [https://quantguild.com](https://quantguild.com)
- [https://gd-sgd.streamlit.app/](https://gd-sgd.streamlit.app/)
- [https://romanmichaelpaolucci.medium.com/](https://romanmichaelpaolucci.medium.com/)
- [https://discord.com/invite/MJ4FU2c6c3](https://discord.com/invite/MJ4FU2c6c3)

## 📝 4. BẢN MÔ TẢ GỐC (DESCRIPTION)
```text
🚀 Master Quantitative Skills with Quant Guild:
https://quantguild.com

Join the Quant Guild Discord server here:
https://discord.com/invite/MJ4FU2c6c3

I hope you enjoyed this lecture visualizing the learning process. Please feel free to leave a comment or reach out to me with any questions.

SG-SGD-SA Application
https://gd-sgd.streamlit.app/

Articles and code walkthroughs can be found on our blog
https://medium.com/quant-guild
https://romanmichaelpaolucci.medium.com/

For more free tutorials and references see our GitHub
https://github.com/RomanMichaelPaolucci
https://github.com/Quant-Guild
```

## 🔊 5. NỘI DUNG NÓI CHI TIẾT (TRANSCRIPT)
> [!TIP]
> Bản dịch này được tải tự động và tối ưu hóa thành các đoạn văn để dễ đọc. Bạn có thể sao chép phần này dán vào Google Translate hoặc nạp thẳng file này vào NotebookLM để học tập tương tác.

Welcome back. It's been quite some time. Today I want to talk to you about convex and non-convex optimization problems. We want to talk about why we should care about these problems. In the first place, we want to talk about the different algorithms we can employ to solve these different types of problems. And I also want to talk about how I've used these algorithms in my own research and how productive each one has been in different types of problems spaces.

So for starters, why should we care about any sort of optimization problem? Well, machine learning and artificial intelligence. The backbone of modern machine learning or artificial intelligence, CzechGPT, Genv and I alone, or whatever model, whatever large language model that you use to generate things, whatever image generation software you use to generate logos or pictures, all of these different models hinge on our ability to train them.

Training is the process of trying to map a set of inputs to a target set of outputs. In the case of CzechGPT, the input is a prompt. And the target is the output response that you expect. CzechGPT, Genv. Now that's a stochastic representation or if more of a probabilistic map rather than deterministic. And by deterministic, I mean when you get at the same prompt at new generate different responses, deterministic is we'll generate the same response every single time.

But nevertheless, our ability to train those models and decrease the error is what leads to better responses. Okay. Complex and non-convex optimization is literally what's going on under the hood of the car. You get into a car you're trying to key, don't even think about what's going on. Right? How long CzechGPT, you even think about what's going on. You know, if you think about the several probably obscene number of majors products that are being paralyzed to compute your answer right in front of your eyes.

But before we even get there, we have to train it and training it is an optimization problem. So what's happening here? I made this app to help visualize the problem space. It's pretty abstract but bear with me I think it's going to make a little bit of sense. So let's talk about this surface that I have in front of me here. Let's suppose that this surface represents error. So x and y are my input and z is the output.

So clearly, if z is my error, so suppose it's the error for say a large language model like CzechGPT. Right? Where do I want to be? Do I want to be on this red point where error is really high? Probably not, right? I want to be all the way down here where error is really low. Now you may say, well, why don't we just look at the bottom of the bowl and pick those x and y points and we'll be done. And that's the parameters that we need for our model.

And that's it and we're done. That is true in this setting, right? We can just pick the x and y down here. We can see it. Boom, just pick those two. But does CzechGPT only have two parameters x and y? I'm afraid not, right? That space is so incredibly large that we couldn't possibly visualize it. So what can we do? What hope do we have? If this is our error, right? This is just a representation of the error function, right?

So that you can understand visually what's going on. How can we possibly find that lowest point on the surface? Well, what we could do is we can employ these different algorithms. We're going to talk about gradient descent, stochastic gradient descent, and simulated a kneeling today. And we're going to talk about them in this controlled setting so that even when you can't visualize what's going on in the higher dimensional spaces, when you're training these neural networks, you can at least have an idea of your break, leave what's going on in terms of the algebra and calculus so that you have, like I said, an idea of what's going on under the hood and how learning is actually occurring and why you might not be able to learn in some cases or why you might have some challenges learning.

So what's the deal with gradient descent? Okay, keep in mind, this is a multivariable function. We have x and y as an input, and z as the output. Now multivariate, multivariable. Okay, why is not a function of x? They're strictly orthogonal. Okay, at least in this setting. So gradient descent, x is zero is a vector. It's a random starting plant. So it's going to be an x and a y, random x and a y. For each iteration t and we specify the number of iterations we want to do, we're going to compute the gradient and if your calculus three is rusty, all the gradient is a collection of partial derivatives.

So you partially differentiate in this case with respect to x and with respect to y. It's going to give you a vector. It's going to point in the direction of greatest increase from the initial point. We're trying to minimize the error because we want good responses. We want to minimize the error of our responses. We're going to step negative that direction. So we're going to compute a new xt. It's going to overwrite the old one.

And what we're going to do is we're going to subtract the gradient vector. Okay, keep in mind it's evaluated at the initial point. That we're given, right? The previous iterations point. We're also going to scale it by a learning rate. This is going to determine how much we should step in each iteration. Remember linear approximations for non-linear functions get worse the further away you go from that. So it makes sense that you should have a learning rate that you can scale some sort of scalar in front of the gradient that you can control.

So what's actually going on? If you don't understand the calculus, how can we understand what's going on? Well, this is gradient descent right here. See this this path of points? That's literally what's happening. So we started this green point and imagine we put a piece of paper up to that green point, a perfectly flat piece of paper. Alpha determines how much we step along that piece of paper. Okay, so when alpha is small like it is right now, point one, we're going to step a little bit.

If alpha is extremely large, we're going to step a lot a bit. Okay, but clearly we want to do this iteratively because if we stepped a piece of paper right away all the way down, we would be off the function over here and we'd be back all the way up here on the z, right? Because we would step in this direction and up over here if we made a really large step, we would be back up here. Okay, so that's why the learning rate is relatively small in this case, right?

And you could see we do this iteratively until we get to the bottom. And that produces the exact same minimum error. So now we have a way of finding the x and y that produces the smallest error even without knowing what the function looks like. We could literally do this purely algorithmically. I didn't need to visualize this surface in order to find the x and y that gives us the smallest error. The one that gets us to the bottom of this surface.

This is a convex function. What's the problem, right? What's the problem with this? Well, if every error function was convex, that would be wonderful. We could train it quite easily wouldn't be computationally intensive. In most cases it wouldn't be intractable. You'd literally just employ gradient descent until you get to the bottom and you minimize the error. It's a problem with this. Well, you know, we're going to disregard the idea of overfitting for now.

We're going to disregard other concerns in the training process and just talk about the actually training and trying to extract the information that we're looking for from a particular model representation. What's the problem here? Well, we we may end up with a non-convex error function. And what a non-convex error function looks like is something like this. Okay. Clearly, we have this start point right here.

We do gradient descent and we end up here at this low point. But is that the lowest low for error that we can get to? Now we can get all the way down here. Right? That's a much better representation of the map of input style put. So if we can get to down here. But I ran gradient descent from this starting point and I ended up here. How on earth can I get here? Well, I could pick a random starting point. But if I don't have any heristics guy, me, I'm going to be picking forever.

I could literally pick for infinity. So guarantee. Right? Add infinity maybe, but you know, nothing tractable. So what what can I do? Right? What can I do here? Now the particularly keen among you may recognize that the z here is actually negative and error will most likely have some measure of distance so it'll be squared or absolute valued so it can't be negative. But bear with me, there's just a representation.

Thank you for this error shifted down if you have to. But how do we get to here? Right? Remember, I can't visualize this function in a higher dimensional space. algebraically, I need a way to get down here. Right? So I want to find a smaller error between my input and output target. One way, one potential way, I should say, is through stochastic gradient descent. Okay? Stochastic gradient descent is the exact same procedure.

Okay? See exact same procedure. The only difference is we're adding noise to the gradient. So we're inducing randomness in each gradient step. All right? The scale of the step is still governed by alpha. And if alpha is arbitrarily large, then we can end up searching a lot of the space. Okay? And what I'm going to do is I'm going to show you what this looks like in a convex setting. It looks quite similar, right?

Because we're inducing a very small amount of noise, but again, we're still ending up where we should be at the bottom here. Right? That's nothing surprising. Let's go on down to the non-convex function here. Right? We see a similar thing happen. But what happens when we increase the learning rate? Just as an example, let's see what happens. Not too much. Maybe to point five. Okay? Now we're starting to explore more of the space.

So instead of just diving right down into the local minimum, we started to explore up a little bit. Keep in mind, this is stochastic. Every time I run this, it's going to be different. I'll increase alpha to point seven. We're exploring significantly more of this space now before we get to this local minimum here. What happens if I make it point eight? Now we're exploring a significantly larger portion of this space.

Right? So this is quite interesting. And perhaps there is a way that we can extend this. Maybe if we have an arbitrarily high learning rate, we can keep a hash map of all the parameters in the corresponding errors and just pick the parameters that yields the lowest error. But that's going to be pretty similar to the idea of simulated and healing. So we're going to get there at a moment. But just for illustration purposes, here it is with a learning rate of almost one.

From the same starting point. So that's exactly what's going on. Now what about with this this convex sort of representation here. Let's scroll back up to this convex representation. You can see that it's essentially just noise. Right? We're going back and forth. It's pretty much just inducing random noise in the gradient. We're going to continue to step back and forth in that fashion. So clearly learning rate is a hybrid parameter that has to be tuned to the problem.

So the Casi gradient descent is one way to get over potential local minimums. Right? Because if you are, let's say, sitting at the top of a hill. Right? Let's say we're sitting at the top of this hill. If we compute the gradient, maybe we're going to step in this direction. Right? That would be great. We would end up all the way down here. But maybe if we just compute it vanilla, we start going this direction.

If we induce noise at the top here, then we have a probability greater than zero of stepping in this direction. Okay? Depending on how large the noise is, it's going to depend on the probability. It's going to change the probability of ending up actually at this global minimum down here. So Casi gradient descent is more of a probabilistic version of gradient descent in a way. We have no ability really to control what's going on because, again, it's a probabilistic algorithm or not probabilistic, but it's a so-castic algorithm.

But we do have the ability to potentially overcome these local minimums. So anything else we could do? Let me talk about one last one that's been particularly productive for me. That is simulated and kneeling. I find it fascinating as an algorithm. Simulated and kneeling, we take a initial starting point, again, it's still a vector. We have some temperature T. And essentially what we're going to do is we are going to generate a random point in the neighborhood of our current point.

We are going to compute a change in functional value. And if the change in functional value at that new point is less, then we're going to step there with certainty. If it's greater, then we are going to step there with a probability that's governed by the change and the temperature. And one way to interpret this is that as the temperature is high, we're bouncing around a lot. But then as the temperature starts to cool off, we're not bouncing around as much.

So it's pretty sweet. It's a pretty cool algorithm. Right? And if I was to say increased the number of iterations here, let's make it pretty big. Let's make it like a 100. And then see if we can see the start, the end, check out some of these local extreme up. So we started at the same point here. Whoops, let me scroll down. So we started at the same green point. We've run 100 iterations of simulated in dealing.

And all of these blue points represent minimums that we've observed. Our guess this is nodes along the last path that we've observed or the optimal path. Yeah. So we observe 100 different minimums per iteration. You can see compared to Cicacic Radiance descent and gradient descent, we actually end up at the global minimum. So this is quite interesting because we explored a significantly large fraction of this space just by doing this a little bit differently.

We didn't use any calculus instead we did a probabilistic search where it's actually we are balancing exploration and exploitation based on our temperature and our cooling rate. So for example if I was to decrease this temperature right off the bat, let's make the temperature one. Will we explore more of the space? Now we actually get very similar results if not the same minimum as Cicacic gradient descent and gradient descent, or at least to Cicacic gradient descent with a low learning rate.

But if we make temperature very large, then we explore much more of the space. Right. So here we end up at this minimum right here. Okay we actually don't end up at this global minimum down here but we end up at this minimum right here. And if we change the cooling rate maybe we cool it a lower rate. We get to a different one. So this is just a different type of optimization algorithm. Again it's quite interesting.

So essentially instead of updating the gradient with or instead of updating the initial starting point with the gradient times the learning or the gradient plus noise times the learning rate, this is the functional representation. We say update it as x prime if delta e is less than zero. So the functional changes less than zero we update it in that direction. Otherwise with probability, exponential negative delta e over t, if delta e is greater than zero.

So with some probability greater than zero, we are going to explore a non optimal step. And then if we don't hit, then we are going to just go with the original point and choose a new random point and then do it again. And that's why we have 100 iterations here. And that is how simulated and healing work. So it's more of a search algorithm really and it can be used in a machine learning context. It can also be used in other types of search problems as well.

So it's quite interesting. So those are the three algorithms I wanted to talk about today. There are different flavors of each that you can use so you can use simulated and healing in the context of stochastic gradient descent perhaps you even have some temperature and cooling rate for your noise and you scale it in that capacity. Then maybe you have a probabilistic rate of acceptance. I mean really just an infinite number of ways that you could possibly establish these optimization algorithms.

But these are a couple of different flavors and they're quite interesting. So I've actually had a lot of luck employing simulated and healing in the context of training variation, a lot of encodes to learn arbitrage free volatility surfaces. Actually preserved the arbitrage free nature of the surface even when generating from the latent space a brand new volatility surface. And that was quite useful in approximating pricing functionals using neural networks is actually to learn the parameters of a model to a volatility surface.

It allowed us to use significantly more data. So simulated and healing in conjunction with stochastic gradient descent and other different optimizers like other other routines like atom, very, very productive. That combination of having like a sort of a simulated and healing style learning rate was extremely effective in sort of surpassing and overcoming those issues of getting stuck at a local minimum.

Because really that's what was happening most of the time is we were trying to learn some sort of optimal representation we wanted to be down here. We would get stuck like right here. And the generated surfaces just wouldn't be any good. But eventually we were able to learn really great representation of the surfaces and that was thanks to a combination of like I said, the simulated and needle, annealing style training with gradient descent.

So that's going to do it for this video. I hope you enjoyed. I just wanted to go over a couple of different algorithms and the context of deep learning, machine learning, neural network training, you know, the the problem is face of really artificial intelligence in general. And you know different ways that we can start to think about how these models are kind of built. You know what's going on under the hood because you know more and more every day I'm seeing you know adults children alike using track GPT, Gemini, Lama maybe maybe less Gemini and Lama but you know you get the gist that everyone seems to be using artificial intelligence but there isn't really an understanding about what's going on in the training process.

You know this has nothing to even do with the reinforcement learning or human human feedback with the reinforcement learning. We talk nothing about different types of learning structures. There's supervised and supervised reinforcement learning and you know there's also reinforcement learning component as well. So this is kind of just the the tip of the iceberg here before we we even start to to get into more sophisticated training methodology.

So I hope you enjoy I hope this um hopefully was enlightening to see how essentially machines learn in the context of you know a 3D visualization of error right we want to get to the lowest point and there are different algorithms that we can use to get to that lowest point. So you know feel free to you know leave a comment if you have any questions you can always reach out to me. I'll leave a link to this app in the description below otherwise I will see you in the next one.