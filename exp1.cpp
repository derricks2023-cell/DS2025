#include <iostream>
#include <vector>
#include <stack>
#include <algorithm>
#include <cmath>
using namespace std;

/*********************** ���ߺ��� ***********************/
void printLine() {
    cout << "--------------------------------------------------\n";
}

/*********************** �� 1 �⣺�������� ***********************/
struct Complex {
    int a; // ʵ��
    int b; // �鲿
};

// ��ӡ��������
void printComplexVector(const vector<Complex> &v) {
    for (auto &x : v)
        cout << "(" << x.a << ", " << x.b << ")  ";
    cout << "\n";
}

// ��ģ����������ģ��չʾ��
bool cmpComplex(const Complex &x, const Complex &y) {
    return (x.a * x.a + x.b * x.b) < (y.a * y.a + y.b * y.b);
}

void part1() {
    cout << "==================== �� 1 �⣺������������ ====================\n\n";

    // ʾ��1������
    {
        cout << ">>> ʾ�� 1������\n";
        vector<Complex> v = {{3,4},{1,-2},{0,5},{-4,-3}};
        cout << "ԭ����:\n"; printComplexVector(v);
        sort(v.begin(), v.end(), cmpComplex);
        cout << "�����:\n"; printComplexVector(v); cout << "\n";
    }

    // ʾ��2������ + ɾ�� + ����
    {
        cout << ">>> ʾ�� 2������ + ɾ�� + ����\n";
        vector<Complex> v = {{2,1},{-1,3}};
        cout << "ԭ����:\n"; printComplexVector(v);

        cout << "���� (4, -2)\n";
        v.push_back({4,-2}); printComplexVector(v);

        cout << "���� (2, 1)\n";
        auto it = find_if(v.begin(), v.end(), [](Complex c){
            return c.a==2 && c.b==1;
        });
        if(it != v.end()) cout << "�ҵ���Ԫ�أ�\n";

        cout << "ɾ�� (2, 1)\n";
        v.erase(it); printComplexVector(v); cout << "\n";
    }

    // ʾ��3��Ψһ�� + ȡǰ m ����
    {
        cout << ">>> ʾ�� 3��Ψһ�� + ǰ m ����\n";
        vector<Complex> v = {{3,3},{1,2},{3,3},{-2,4},{-2,4},{0,0}};
        cout << "ԭ����:\n"; printComplexVector(v);

        sort(v.begin(), v.end(), [](Complex x, Complex y){
            if(x.a == y.a) return x.b < y.b;
            return x.a < y.a;
        });

        v.erase(unique(v.begin(), v.end(), [](Complex x, Complex y){
            return (x.a==y.a && x.b==y.b);
        }), v.end());

        cout << "Ψһ����:\n"; printComplexVector(v);

        sort(v.begin(), v.end(), cmpComplex);
        int m = 3;
        cout << "ȡǰ " << m << " ����:\n";
        for(int i = (int)v.size()-1; i >= (int)v.size()-m; i--)
            cout << "(" << v[i].a << ", " << v[i].b << ")  ";
        cout << "\n\n";
    }
}

/*********************** �� 2 �⣺���ʽ��ֵ��ջ�� ***********************/
int priority(char op) {
    if(op=='!') return 3;
    if(op=='^') return 2;
    if(op=='*' || op=='/') return 1;
    if(op=='+' || op=='-') return 0;
    return -1;
}

int factorial(int n){
    int ans=1;
    for(int i=1;i<=n;i++) ans*=i;
    return ans;
}

int apply(int a, int b, char op){
    switch(op){
        case '+': return b + a;
        case '-': return b - a;
        case '*': return b * a;
        case '/': return b / a;
        case '^': return pow(b, a);
    }
    return 0;
}

int eval(string exp){
    stack<int> nums;
    stack<char> ops;

    for(int i=0;i<exp.size();i++){
        if(isdigit(exp[i])){
            int val=0;
            while(i<exp.size() && isdigit(exp[i])){
                val=val*10 + exp[i]-'0';
                i++;
            }
            i--;
            nums.push(val);
        } else if(exp[i] == '('){
            ops.push('(');
        } else if(exp[i] == ')'){
            while(ops.top()!='('){
                char op = ops.top(); ops.pop();
                if(op=='!'){
                    int a = nums.top(); nums.pop();
                    nums.push(factorial(a));
                }else{
                    int a=nums.top(); nums.pop();
                    int b=nums.top(); nums.pop();
                    nums.push(apply(a,b,op));
                }
            }
            ops.pop();
        } else {
            while(!ops.empty() && ops.top()!='(' &&
                  priority(ops.top()) >= priority(exp[i])){
                char op = ops.top(); ops.pop();
                if(op=='!'){
                    int a = nums.top(); nums.pop();
                    nums.push(factorial(a));
                }else{
                    int a=nums.top(); nums.pop();
                    int b=nums.top(); nums.pop();
                    nums.push(apply(a,b,op));
                }
            }
            ops.push(exp[i]);
        }
    }

    while(!ops.empty()){
        char op = ops.top(); ops.pop();
        if(op=='!'){
            int a = nums.top(); nums.pop();
            nums.push(factorial(a));
        }else{
            int a=nums.top(); nums.pop();
            int b=nums.top(); nums.pop();
            nums.push(apply(a,b,op));
        }
    }
    return nums.top();
}

void part2(){
    cout << "==================== �� 2 �⣺���ʽ��ֵ ====================\n\n";
    vector<string> exps = {
        "1+2", "2*3+4", "(2+3)*4", "5!-4", "2^3+1",
        "10/(2+3)", "3+4*2/(1-5)", "(3+2)!-1", "6/3*2+5", "8-3^2+1"
    };

    for(int i=0;i<exps.size();i++){
        cout << "ʾ�� " << i+1 << ": " << exps[i] << "\n";
        cout << "��� = " << eval(exps[i]) << "\n\n";
    }
}

/*********************** �� 3 �⣺��������� ***********************/
int largestRectangle(vector<int> h){
    stack<int> st;
    h.push_back(0);
    int maxA = 0;
    for(int i=0;i<h.size();i++){
        while(!st.empty() && h[st.top()] > h[i]){
            int height = h[st.top()]; st.pop();
            int left = st.empty()? -1 : st.top();
            maxA = max(maxA, height * (i - left - 1));
        }
        st.push(i);
    }
    return maxA;
}

void part3(){
    cout << "==================== �� 3 �⣺��������� ====================\n\n";
    vector<vector<int>> tests = {
        {6,2,5,4,5,1,6},
        {2,1,5,6,2,3},
        {4,4,4,4}
    };

    for(int i=0;i<tests.size();i++){
        cout << "ʾ�� " << i+1 << ":\n���� heights = [ ";
        for(int x : tests[i]) cout << x << " ";
        cout << "]\n";
        cout << "��������� = " << largestRectangle(tests[i]) << "\n\n";
    }
}

/*********************** ������ ***********************/
int main(){
    part1(); printLine();
    part2(); printLine();
    part3();
    return 0;
}

