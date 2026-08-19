#include "sha256.hpp"

#include <array>
#include <fstream>
#include <iomanip>
#include <sstream>

namespace enginetest::runtime {
namespace {
constexpr std::array<std::uint32_t, 64> K = {
  0x428a2f98u,0x71374491u,0xb5c0fbcfu,0xe9b5dba5u,0x3956c25bu,0x59f111f1u,0x923f82a4u,0xab1c5ed5u,
  0xd807aa98u,0x12835b01u,0x243185beu,0x550c7dc3u,0x72be5d74u,0x80deb1feu,0x9bdc06a7u,0xc19bf174u,
  0xe49b69c1u,0xefbe4786u,0x0fc19dc6u,0x240ca1ccu,0x2de92c6fu,0x4a7484aau,0x5cb0a9dcu,0x76f988dau,
  0x983e5152u,0xa831c66du,0xb00327c8u,0xbf597fc7u,0xc6e00bf3u,0xd5a79147u,0x06ca6351u,0x14292967u,
  0x27b70a85u,0x2e1b2138u,0x4d2c6dfcu,0x53380d13u,0x650a7354u,0x766a0abbu,0x81c2c92eu,0x92722c85u,
  0xa2bfe8a1u,0xa81a664bu,0xc24b8b70u,0xc76c51a3u,0xd192e819u,0xd6990624u,0xf40e3585u,0x106aa070u,
  0x19a4c116u,0x1e376c08u,0x2748774cu,0x34b0bcb5u,0x391c0cb3u,0x4ed8aa4au,0x5b9cca4fu,0x682e6ff3u,
  0x748f82eeu,0x78a5636fu,0x84c87814u,0x8cc70208u,0x90befffau,0xa4506cebu,0xbef9a3f7u,0xc67178f2u
};
constexpr std::uint32_t rotr(std::uint32_t x, unsigned n) { return (x >> n) | (x << (32 - n)); }
constexpr std::uint32_t ch(std::uint32_t x,std::uint32_t y,std::uint32_t z){return (x&y)^((~x)&z);}
constexpr std::uint32_t maj(std::uint32_t x,std::uint32_t y,std::uint32_t z){return (x&y)^(x&z)^(y&z);}
constexpr std::uint32_t bs0(std::uint32_t x){return rotr(x,2)^rotr(x,13)^rotr(x,22);}
constexpr std::uint32_t bs1(std::uint32_t x){return rotr(x,6)^rotr(x,11)^rotr(x,25);}
constexpr std::uint32_t ss0(std::uint32_t x){return rotr(x,7)^rotr(x,18)^(x>>3);}
constexpr std::uint32_t ss1(std::uint32_t x){return rotr(x,17)^rotr(x,19)^(x>>10);}

class Sha256 {
    std::array<std::uint32_t,8> h_ = {0x6a09e667u,0xbb67ae85u,0x3c6ef372u,0xa54ff53au,0x510e527fu,0x9b05688cu,0x1f83d9abu,0x5be0cd19u};
    std::array<std::uint8_t,64> buf_{};
    std::uint64_t bits_=0; std::size_t used_=0;
    void block(const std::uint8_t* p){
        std::array<std::uint32_t,64>w{};
        for(int i=0;i<16;++i) w[i]=(std::uint32_t(p[i*4])<<24)|(std::uint32_t(p[i*4+1])<<16)|(std::uint32_t(p[i*4+2])<<8)|p[i*4+3];
        for(int i=16;i<64;++i) w[i]=ss1(w[i-2])+w[i-7]+ss0(w[i-15])+w[i-16];
        auto a=h_[0],b=h_[1],c=h_[2],d=h_[3],e=h_[4],f=h_[5],g=h_[6],hh=h_[7];
        for(int i=0;i<64;++i){auto t1=hh+bs1(e)+ch(e,f,g)+K[i]+w[i];auto t2=bs0(a)+maj(a,b,c);hh=g;g=f;f=e;e=d+t1;d=c;c=b;b=a;a=t1+t2;}
        h_[0]+=a;h_[1]+=b;h_[2]+=c;h_[3]+=d;h_[4]+=e;h_[5]+=f;h_[6]+=g;h_[7]+=hh;
    }
public:
    void update(const std::uint8_t* p,std::size_t n){bits_ += std::uint64_t(n)*8; while(n){auto take=std::min(n,buf_.size()-used_);std::copy(p,p+take,buf_.begin()+used_);used_+=take;p+=take;n-=take;if(used_==64){block(buf_.data());used_=0;}}}
    std::string finish(){buf_[used_++]=0x80;if(used_>56){while(used_<64)buf_[used_++]=0;block(buf_.data());used_=0;}while(used_<56)buf_[used_++]=0;for(int i=7;i>=0;--i)buf_[used_++]=std::uint8_t(bits_>>(i*8));block(buf_.data());std::ostringstream o;o<<std::hex<<std::setfill('0');for(auto v:h_)o<<std::setw(8)<<v;return o.str();}
};
}

std::string sha256_file(const std::string& path){std::ifstream f(path,std::ios::binary);if(!f)return {};Sha256 s;std::array<std::uint8_t,64*1024>b{};while(f){f.read(reinterpret_cast<char*>(b.data()),b.size());auto n=f.gcount();if(n>0)s.update(b.data(),static_cast<std::size_t>(n));}return s.finish();}

} // namespace enginetest::runtime
